"""Adapters for the old pygame board format and python-chess.

The old local game stores pieces as strings such as ``"wP"``, ``"bK"``, and
``"--"`` in an 8x8 array where row 0 is rank 8. The ML stack uses
``python-chess`` because FEN, UCI, PGN, legal moves, and engine integration are
standard there.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import chess


INTERNAL_TO_SYMBOL = {
    "wP": "P",
    "wN": "N",
    "wB": "B",
    "wR": "R",
    "wQ": "Q",
    "wK": "K",
    "bP": "p",
    "bN": "n",
    "bB": "b",
    "bR": "r",
    "bQ": "q",
    "bK": "k",
}
SYMBOL_TO_INTERNAL = {value: key for key, value in INTERNAL_TO_SYMBOL.items()}


@dataclass(frozen=True)
class InternalMoveDict:
    r1: int
    c1: int
    r2: int
    c2: int
    promotion: str | None = None


def _square_from_internal(row: int, col: int) -> chess.Square:
    return chess.square(col, 7 - row)


def _internal_from_square(square: chess.Square) -> tuple[int, int]:
    return 7 - chess.square_rank(square), chess.square_file(square)


def internal_board_to_chess(
    board: Sequence[Sequence[str]],
    *,
    white_to_move: bool = True,
    castling_rights: str = "KQkq",
    en_passant: tuple[int, int] | None = None,
    halfmove_clock: int = 0,
    fullmove_number: int = 1,
) -> chess.Board:
    """Convert an old CHESS V2 8x8 board array into a python-chess Board."""

    if len(board) != 8 or any(len(row) != 8 for row in board):
        raise ValueError("internal board must be an 8x8 sequence")

    chess_board = chess.Board.empty()
    for row_idx, row in enumerate(board):
        for col_idx, piece in enumerate(row):
            if piece == "--":
                continue
            symbol = INTERNAL_TO_SYMBOL.get(piece)
            if symbol is None:
                raise ValueError(f"unknown internal piece code: {piece!r}")
            chess_board.set_piece_at(
                _square_from_internal(row_idx, col_idx),
                chess.Piece.from_symbol(symbol),
            )

    chess_board.turn = chess.WHITE if white_to_move else chess.BLACK
    chess_board.castling_rights = chess.Board().castling_rights
    chess_board.set_castling_fen(castling_rights if castling_rights else "-")
    chess_board.ep_square = None if en_passant is None else _square_from_internal(*en_passant)
    chess_board.halfmove_clock = halfmove_clock
    chess_board.fullmove_number = fullmove_number
    return chess_board


def chess_board_to_internal(board: chess.Board) -> list[list[str]]:
    """Convert a python-chess Board into the old 8x8 CHESS V2 board array."""

    rows = [["--" for _ in range(8)] for _ in range(8)]
    for square, piece in board.piece_map().items():
        row, col = _internal_from_square(square)
        rows[row][col] = SYMBOL_TO_INTERNAL[piece.symbol()]
    return rows


def internal_move_to_uci(
    start: tuple[int, int],
    end: tuple[int, int],
    promotion: str | None = None,
) -> str:
    """Convert row/column move coordinates into UCI."""

    move = chess.Move(_square_from_internal(*start), _square_from_internal(*end), promotion=_promotion_piece(promotion))
    return move.uci()


def chess_move_to_internal_dict(move: chess.Move) -> InternalMoveDict:
    r1, c1 = _internal_from_square(move.from_square)
    r2, c2 = _internal_from_square(move.to_square)
    promotion = chess.piece_symbol(move.promotion).upper() if move.promotion else None
    return InternalMoveDict(r1=r1, c1=c1, r2=r2, c2=c2, promotion=promotion)


def _promotion_piece(promotion: str | None) -> chess.PieceType | None:
    if promotion is None:
        return None
    lookup = {"Q": chess.QUEEN, "R": chess.ROOK, "B": chess.BISHOP, "N": chess.KNIGHT}
    try:
        return lookup[promotion.upper()]
    except KeyError as exc:
        raise ValueError("promotion must be one of Q, R, B, N") from exc
