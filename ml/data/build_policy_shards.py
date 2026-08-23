"""Build sharded human-policy datasets from PGN files."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import chess
import pyarrow as pa
import pyarrow.parquet as pq
from tqdm import tqdm

from ml.common.board_encoder import BOARD_ENCODER_VERSION
from ml.common.move_encoder import MOVE_VOCAB_VERSION, encode_move
from ml.data.schemas import DatasetMetadata
from ml.data.stream_pgn import parse_rating, stream_games


def game_is_usable(game, min_plies: int, min_rating: int | None, max_rating: int | None) -> bool:
    white_rating = parse_rating(game.headers.get("WhiteElo"))
    black_rating = parse_rating(game.headers.get("BlackElo"))
    if white_rating is None or black_rating is None:
        return False
    if min_rating is not None and (white_rating < min_rating or black_rating < min_rating):
        return False
    if max_rating is not None and (white_rating > max_rating or black_rating > max_rating):
        return False
    return sum(1 for _ in game.mainline_moves()) >= min_plies


def iter_policy_rows(game, game_id: str):
    board = game.board()
    ratings = {
        chess.WHITE: parse_rating(game.headers.get("WhiteElo")),
        chess.BLACK: parse_rating(game.headers.get("BlackElo")),
    }
    time_control = game.headers.get("TimeControl", "?")
    for ply, move in enumerate(game.mainline_moves()):
        if move not in board.legal_moves:
            break
        yield {
            "game_id": game_id,
            "ply": ply,
            "fen": board.fen(),
            "player_rating": ratings[board.turn],
            "time_control": time_control,
            "move_uci": move.uci(),
            "move_index": encode_move(move),
        }
        board.push(move)


def write_shard(rows: list[dict], output_dir: Path, shard_index: int) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist(rows)
    path = output_dir / f"policy_{shard_index:06d}.parquet"
    pq.write_table(table, path, compression="zstd")
    return path


def build_policy_shards(
    input_pgn: str | Path,
    output_dir: str | Path,
    *,
    shard_size: int = 100_000,
    min_plies: int = 12,
    min_rating: int | None = None,
    max_rating: int | None = None,
    max_games: int | None = None,
) -> dict:
    output_dir = Path(output_dir)
    rows: list[dict] = []
    shard_index = 0
    metadata = DatasetMetadata(
        dataset_name="human_policy_v1",
        encoder_version=BOARD_ENCODER_VERSION,
        move_vocab_version=MOVE_VOCAB_VERSION,
        source_filename=str(input_pgn),
    )

    for game_index, game in enumerate(tqdm(stream_games(input_pgn), desc="PGN games")):
        if max_games is not None and game_index >= max_games:
            break
        metadata.games_processed += 1
        game_id = game.headers.get("Site") or f"game_{game_index}"
        if not game_is_usable(game, min_plies, min_rating, max_rating):
            metadata.samples_rejected += 1
            continue
        for row in iter_policy_rows(game, game_id):
            metadata.positions_processed += 1
            metadata.samples_accepted += 1
            rating = row["player_rating"]
            metadata.rating_min = rating if metadata.rating_min is None else min(metadata.rating_min, rating)
            metadata.rating_max = rating if metadata.rating_max is None else max(metadata.rating_max, rating)
            rows.append(row)
            if len(rows) >= shard_size:
                write_shard(rows, output_dir, shard_index)
                shard_index += 1
                rows = []

    if rows:
        write_shard(rows, output_dir, shard_index)
    metadata_path = output_dir / "metadata.json"
    metadata_path.write_text(json.dumps(metadata.to_dict(), indent=2), encoding="utf-8")
    return metadata.to_dict()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="Path to .pgn or .pgn.zst")
    parser.add_argument("--output", default="data/shards/policy/train")
    parser.add_argument("--shard-size", type=int, default=100_000)
    parser.add_argument("--max-games", type=int, default=None)
    parser.add_argument("--min-rating", type=int, default=None)
    parser.add_argument("--max-rating", type=int, default=None)
    args = parser.parse_args()
    metadata = build_policy_shards(
        args.input,
        args.output,
        shard_size=args.shard_size,
        max_games=args.max_games,
        min_rating=args.min_rating,
        max_rating=args.max_rating,
    )
    print(json.dumps(metadata, indent=2))


if __name__ == "__main__":
    main()
