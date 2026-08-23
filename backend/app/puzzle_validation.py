"""Validate puzzle FEN and UCI sequences before storage."""

from __future__ import annotations

import chess


def validate_puzzle(fen: str, moves_uci: list[str]) -> tuple[bool, str]:
    try:
        board = chess.Board(fen)
    except ValueError as exc:
        return False, f"Invalid FEN: {exc}"

    for index, move_uci in enumerate(moves_uci):
        try:
            move = chess.Move.from_uci(move_uci)
        except ValueError:
            return False, f"Invalid UCI at index {index}: {move_uci}"
        if move not in board.legal_moves:
            return False, f"Illegal move at index {index}: {move_uci}"
        board.push(move)

    return True, "Puzzle is valid"
