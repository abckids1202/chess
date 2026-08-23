"""Reusable Stockfish process wrapper.

Keep one UCI engine process alive and reuse it for every move. Creating a new
process for every request is slow and can leave orphaned Stockfish processes.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Optional

import chess
import chess.engine


class StockfishBot:
    def __init__(self, stockfish_path: str, skill_level: int = 5, move_time: float = 0.5):
        self.stockfish_path = str(Path(stockfish_path).expanduser())
        self.skill_level = max(0, min(20, int(skill_level)))
        self.move_time = max(0.01, float(move_time))
        self._lock = threading.Lock()

        if not Path(self.stockfish_path).is_file():
            raise FileNotFoundError(f"Stockfish executable not found: {self.stockfish_path}")

        self.engine = chess.engine.SimpleEngine.popen_uci(self.stockfish_path)
        self.set_skill_level(self.skill_level)

    def set_skill_level(self, skill_level: int):
        self.skill_level = max(0, min(20, int(skill_level)))
        with self._lock:
            self.engine.configure({"Skill Level": self.skill_level})

    def choose_move(self, board: chess.Board, move_time: Optional[float] = None) -> chess.Move:
        if board.is_game_over(claim_draw=True):
            raise ValueError("cannot choose a move in a finished game")
        limit = max(0.01, float(move_time if move_time is not None else self.move_time))
        with self._lock:
            result = self.engine.play(board, chess.engine.Limit(time=limit))
        if result.move is None:
            raise RuntimeError("Stockfish returned no move")
        return result.move

    def analyze_position(self, board: chess.Board, time_limit: float = 0.5):
        with self._lock:
            return self.engine.analyse(
                board,
                chess.engine.Limit(time=max(0.01, float(time_limit))),
            )

    def close(self):
        with self._lock:
            if self.engine is not None:
                self.engine.quit()
                self.engine = None

    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc_value, _traceback):
        self.close()
