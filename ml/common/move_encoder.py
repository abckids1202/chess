"""Fixed neural action vocabulary for CHESS V2 policy models."""

from __future__ import annotations

import chess


MOVE_VOCAB_VERSION = 1
PROMOTION_PIECES = (chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT)
PROMOTION_TO_OFFSET = {piece: index for index, piece in enumerate(PROMOTION_PIECES)}
OFFSET_TO_PROMOTION = {index: piece for piece, index in PROMOTION_TO_OFFSET.items()}

NORMAL_MOVE_COUNT = 64 * 64
PROMOTION_MOVE_COUNT = 64 * 64 * len(PROMOTION_PIECES)
NUM_MOVES = NORMAL_MOVE_COUNT + PROMOTION_MOVE_COUNT


def encode_move(move: chess.Move) -> int:
    """Map a chess.Move to a stable integer action index."""

    base = move.from_square * 64 + move.to_square
    if move.promotion is None:
        return base
    try:
        promo_offset = PROMOTION_TO_OFFSET[move.promotion]
    except KeyError as exc:
        raise ValueError(f"unsupported promotion piece: {move.promotion}") from exc
    return NORMAL_MOVE_COUNT + base * len(PROMOTION_PIECES) + promo_offset


def decode_move(index: int) -> chess.Move:
    """Map a stable integer action index back to a chess.Move."""

    if index < 0 or index >= NUM_MOVES:
        raise ValueError(f"move index out of range: {index}")
    if index < NORMAL_MOVE_COUNT:
        from_square, to_square = divmod(index, 64)
        return chess.Move(from_square, to_square)
    promo_index = index - NORMAL_MOVE_COUNT
    base, promo_offset = divmod(promo_index, len(PROMOTION_PIECES))
    from_square, to_square = divmod(base, 64)
    return chess.Move(from_square, to_square, promotion=OFFSET_TO_PROMOTION[promo_offset])


MOVE_TO_INDEX = {decode_move(index).uci(): index for index in range(NUM_MOVES)}
INDEX_TO_MOVE = {index: decode_move(index) for index in range(NUM_MOVES)}


def build_legal_move_mask(board: chess.Board, *, illegal_value: float = float("-inf")):
    """Return a torch mask where legal moves are 0 and illegal moves are -inf."""

    import torch

    mask = torch.full((NUM_MOVES,), illegal_value, dtype=torch.float32)
    for move in board.legal_moves:
        mask[encode_move(move)] = 0.0
    return mask


def build_legal_move_bool_mask(board: chess.Board):
    """Return a boolean torch mask with True for legal actions."""

    import torch

    mask = torch.zeros((NUM_MOVES,), dtype=torch.bool)
    for move in board.legal_moves:
        mask[encode_move(move)] = True
    return mask
