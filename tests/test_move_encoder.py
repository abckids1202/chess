import chess

from ml.common.move_encoder import NUM_MOVES, decode_move, encode_move


def round_trip(uci):
    move = chess.Move.from_uci(uci)
    assert decode_move(encode_move(move)) == move


def test_normal_move_round_trip():
    round_trip("e2e4")


def test_castling_round_trip():
    round_trip("e1g1")
    round_trip("e8c8")


def test_en_passant_round_trip():
    round_trip("e5d6")


def test_promotions_round_trip():
    for suffix in ("q", "r", "b", "n"):
        round_trip(f"a7a8{suffix}")


def test_legal_move_mask_marks_only_legal_moves():
    import pytest

    pytest.importorskip("torch")
    from ml.common.move_encoder import build_legal_move_bool_mask

    board = chess.Board()
    mask = build_legal_move_bool_mask(board)
    assert mask.shape[0] == NUM_MOVES
    assert mask[encode_move(chess.Move.from_uci("e2e4"))]
    assert not mask[encode_move(chess.Move.from_uci("e2e5"))]
