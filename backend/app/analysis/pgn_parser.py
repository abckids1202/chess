"""Safe PGN parsing and mainline replay for Chess V2 analysis."""

from __future__ import annotations

import io
from typing import Any

import chess
import chess.pgn


class PGNParseError(ValueError):
    """Raised when pasted PGN cannot be replayed as a legal chess game."""


def parse_pgn(pgn_text: str, max_plies: int = 120) -> dict[str, Any]:
    if not pgn_text or not pgn_text.strip():
        raise PGNParseError("Please paste a PGN before analyzing the game.")
    if max_plies < 1:
        raise PGNParseError("The analysis length must be at least one ply.")
    try:
        game = chess.pgn.read_game(io.StringIO(pgn_text))
    except (ValueError, IndexError, TypeError) as exc:
        raise PGNParseError("Could not parse PGN. Please paste a standard chess PGN.") from exc
    if game is None:
        raise PGNParseError("Could not parse PGN. Please paste a standard chess PGN.")
    if game.errors:
        raise PGNParseError(f"This PGN contains an invalid move: {game.errors[0]}")

    board = game.board()
    moves = []
    all_moves = list(game.mainline_moves())
    for move in all_moves[:max_plies]:
        if move not in board.legal_moves:
            raise PGNParseError("This PGN contains an illegal or unsupported move.")
        fen_before = board.fen()
        color = "white" if board.turn == chess.WHITE else "black"
        move_number = board.fullmove_number
        san = board.san(move)
        board.push(move)
        moves.append({
            "ply": len(moves) + 1,
            "move_number": move_number,
            "color": color,
            "uci": move.uci(),
            "san": san,
            "fen_before": fen_before,
            "fen_after": board.fen(),
        })
    if not moves:
        raise PGNParseError("The PGN was parsed, but it contains no moves.")
    return {
        "headers": dict(game.headers),
        "moves": moves,
        "result": game.headers.get("Result", "*") or "*",
        "truncated": len(all_moves) > max_plies,
    }
