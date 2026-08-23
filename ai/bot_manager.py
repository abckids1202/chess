"""GUI-safe bot manager.

The game should call this file instead of importing PyTorch directly. Today it
supports neural policy bots; later it can route to style-policy or policy-value
search bots without changing the UI.
"""

from __future__ import annotations

import chess


class BotManager:
    def __init__(self):
        self.bot = None

    def load_human_policy_bot(self, model_path: str, rating: int, **kwargs):
        from ml.bot.inference import HumanPolicyBot

        self.bot = HumanPolicyBot(model_path=model_path, rating=rating, **kwargs)
        return self.bot

    def choose_move(self, board_or_fen) -> chess.Move:
        if self.bot is None:
            raise RuntimeError("no bot loaded")
        board = chess.Board(board_or_fen) if isinstance(board_or_fen, str) else board_or_fen
        return self.bot.choose_move(board)
