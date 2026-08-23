"""Deterministic board encoder shared by every CHESS V2 neural model.

Orientation v1 is absolute:
- tensor row 0 is chess rank 1
- tensor row 7 is chess rank 8
- tensor column 0 is file a

This does not flip black-to-move positions. The upside is that every model sees
the same physical board coordinates at training and inference time.
"""

from __future__ import annotations

import numpy as np
import chess


BOARD_ENCODER_VERSION = 1
NUM_BOARD_PLANES = 18
BOARD_SHAPE = (NUM_BOARD_PLANES, 8, 8)

PIECE_TO_PLANE = {
    (chess.WHITE, chess.PAWN): 0,
    (chess.WHITE, chess.KNIGHT): 1,
    (chess.WHITE, chess.BISHOP): 2,
    (chess.WHITE, chess.ROOK): 3,
    (chess.WHITE, chess.QUEEN): 4,
    (chess.WHITE, chess.KING): 5,
    (chess.BLACK, chess.PAWN): 6,
    (chess.BLACK, chess.KNIGHT): 7,
    (chess.BLACK, chess.BISHOP): 8,
    (chess.BLACK, chess.ROOK): 9,
    (chess.BLACK, chess.QUEEN): 10,
    (chess.BLACK, chess.KING): 11,
}


def square_to_row_col(square: chess.Square) -> tuple[int, int]:
    return chess.square_rank(square), chess.square_file(square)


def encode_board(board: chess.Board) -> np.ndarray:
    """Encode a python-chess board as an ``18 x 8 x 8`` float32 tensor."""

    planes = np.zeros(BOARD_SHAPE, dtype=np.float32)

    for square, piece in board.piece_map().items():
        row, col = square_to_row_col(square)
        planes[PIECE_TO_PLANE[(piece.color, piece.piece_type)], row, col] = 1.0

    if board.turn == chess.WHITE:
        planes[12, :, :] = 1.0
    if board.has_kingside_castling_rights(chess.WHITE):
        planes[13, :, :] = 1.0
    if board.has_queenside_castling_rights(chess.WHITE):
        planes[14, :, :] = 1.0
    if board.has_kingside_castling_rights(chess.BLACK):
        planes[15, :, :] = 1.0
    if board.has_queenside_castling_rights(chess.BLACK):
        planes[16, :, :] = 1.0
    if board.ep_square is not None:
        row, col = square_to_row_col(board.ep_square)
        planes[17, row, col] = 1.0

    return planes


def encode_board_tensor(board: chess.Board):
    """Encode a board as a torch tensor without requiring torch at import time."""

    import torch

    return torch.from_numpy(encode_board(board))
