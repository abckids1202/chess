"""Compatibility layer between CHESS V2 game code and standard chess objects."""

from .adapter import (
    chess_board_to_internal,
    chess_move_to_internal_dict,
    internal_board_to_chess,
    internal_move_to_uci,
)
from .game_controller import GameController, MoveRecord

__all__ = [
    "chess_board_to_internal",
    "chess_move_to_internal_dict",
    "internal_board_to_chess",
    "internal_move_to_uci",
    "GameController",
    "MoveRecord",
]
