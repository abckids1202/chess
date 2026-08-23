import chess
import numpy as np

from ml.common.board_encoder import encode_board


def test_initial_position_piece_locations():
    planes = encode_board(chess.Board())
    assert planes.shape == (18, 8, 8)
    assert planes[0, 1, 4] == 1.0  # white pawn e2
    assert planes[5, 0, 4] == 1.0  # white king e1
    assert planes[6, 6, 4] == 1.0  # black pawn e7
    assert planes[11, 7, 4] == 1.0  # black king e8
    assert np.all(planes[12] == 1.0)


def test_castling_and_en_passant_planes():
    board = chess.Board()
    board.push_san("e4")
    planes = encode_board(board)
    assert np.all(planes[12] == 0.0)
    assert planes[17, 2, 4] == 1.0  # e3, absolute rank/file orientation
    assert np.all(planes[13] == 1.0)
    assert np.all(planes[16] == 1.0)


def test_custom_fen_black_to_move():
    board = chess.Board("8/8/8/8/8/8/4k3/4K3 b - - 0 1")
    planes = encode_board(board)
    assert planes[5, 0, 4] == 1.0
    assert planes[11, 1, 4] == 1.0
    assert np.all(planes[12] == 0.0)
