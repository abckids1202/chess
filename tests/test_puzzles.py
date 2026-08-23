import chess

from puzzles.puzzle_session import PuzzleSession
from puzzles.puzzle_importer import import_puzzles
from puzzles.puzzle_validator import normalize_record


def test_lichess_trigger_move_becomes_solver_position():
    record = normalize_record({
        "PuzzleId": "sample",
        "FEN": chess.STARTING_FEN,
        "Moves": "e2e4 e7e5 g1f3",
        "Rating": "1000",
        "Themes": "opening",
    })
    assert record["trigger_move"] == "e2e4"
    assert record["solver_fen"].split()[1] == "b"
    assert record["solution_moves"] == ["e7e5", "g1f3"]


def test_puzzle_session_rejects_wrong_move_and_accepts_sequence():
    puzzle = normalize_record({
        "id": "sample",
        "fen": chess.STARTING_FEN,
        "moves_uci": "e2e4 e7e5 g1f3",
    })
    session = PuzzleSession(puzzle)
    assert session.submit_player_move("d2d4")["reason"] == "wrong_move"
    assert session.submit_player_move("e7e5")["ok"]
    assert session.play_forced_reply() == "g1f3"
    assert session.complete


def test_importer_reads_compressed_csv(tmp_path):
    import zstandard as zstd

    csv_text = "PuzzleId,FEN,Moves,Rating,Themes\n" + (
        "sample,\"" + chess.STARTING_FEN + "\",\"e2e4 e7e5\",1000,opening\n"
    )
    source = tmp_path / "puzzles.csv.zst"
    source.write_bytes(zstd.ZstdCompressor().compress(csv_text.encode()))
    output = tmp_path / "normalized.json"
    assert import_puzzles(source, output, limit=1) == 1
