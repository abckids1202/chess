"""Small, explicit helpers for standard chess move conversion."""

from __future__ import annotations

import chess


def legal_moves(board: chess.Board) -> list[chess.Move]:
    return list(board.legal_moves)


def uci_to_move(board: chess.Board, move_uci: str) -> chess.Move:
    move = chess.Move.from_uci(move_uci)
    if move not in board.legal_moves:
        raise ValueError(f"illegal move: {move_uci}")
    return move


def move_to_san(board: chess.Board, move: chess.Move | str) -> str:
    if isinstance(move, str):
        move = chess.Move.from_uci(move)
    return board.san(move)
