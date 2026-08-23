import chess

from chess_core.game_controller import GameController


def test_controller_special_moves_and_undo():
    game = GameController()
    game.push_uci("e2e4")
    game.push_uci("a7a5")
    game.push_uci("e4e5")
    game.push_uci("d7d5")
    record = game.push_uci("e5d6")
    assert record.captured == "p"
    assert game.board.piece_at(chess.D6).symbol() == "P"
    game.undo()
    assert game.board.fen().split()[0] == "rnbqkbnr/1pp1pppp/8/p2pP3/8/8/PPPP1PPP/RNBQKBNR"


def test_controller_rejects_illegal_moves_and_exports_pgn():
    game = GameController()
    try:
        game.push_uci("e2e5")
    except ValueError:
        pass
    else:
        raise AssertionError("illegal move was accepted")
    game.push_uci("e2e4")
    assert "e4" in game.pgn()
    assert game.fen().split()[1] == "b"
