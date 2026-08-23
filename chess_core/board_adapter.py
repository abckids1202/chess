"""Public board adapter module kept separate from the legacy compatibility API."""

from .adapter import chess_board_to_internal, internal_board_to_chess

__all__ = ["chess_board_to_internal", "internal_board_to_chess"]
