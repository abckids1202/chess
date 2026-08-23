"""PGN import/export helpers for completed local games."""

from __future__ import annotations

import io

import chess
import chess.pgn


def board_to_pgn(board: chess.Board, *, headers: dict[str, str] | None = None) -> str:
    game = chess.pgn.Game()
    if headers:
        for key, value in headers.items():
            game.headers[key] = str(value)
    node = game
    replay = chess.Board()
    for move in board.move_stack:
        node = node.add_variation(move)
        replay.push(move)
    game.headers["Result"] = board.result(claim_draw=True)
    return str(game) + "\n"


def pgn_to_board(pgn_text: str) -> chess.Board:
    game = chess.pgn.read_game(io.StringIO(pgn_text))
    if game is None:
        raise ValueError("PGN contains no game")
    board = game.board()
    for move in game.mainline_moves():
        board.push(move)
    return board
