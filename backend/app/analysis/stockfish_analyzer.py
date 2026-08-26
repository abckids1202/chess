"""Small adapter around the shared Chess V2 Stockfish process."""

from __future__ import annotations

from typing import Any, Optional

import chess

from ..stockfish_bot import StockfishBot
from .engine_score import score_from_info


class StockfishAnalyzer:
    def __init__(
        self,
        stockfish_path: Optional[str] = None,
        analysis_time: float = 0.25,
        depth: Optional[int] = None,
        engine: Optional[StockfishBot] = None,
    ):
        self.analysis_time = max(0.05, min(5.0, float(analysis_time)))
        self.depth = depth
        self.engine = engine
        self._owns_engine = engine is None
        if engine is None:
            if not stockfish_path:
                raise FileNotFoundError("Stockfish path is not configured.")
            self.engine = StockfishBot(stockfish_path, move_time=self.analysis_time)

    def analyze_position(self, board: chess.Board) -> dict[str, Any]:
        info = self.engine.analyze_position(board, time_limit=self.analysis_time)
        pv = info.get("pv") or []
        best_move = pv[0] if pv else None
        return {
            "score": score_from_info(info),
            "best_move": best_move,
            "pv": [move.uci() for move in pv[:8]],
        }

    def get_best_move(self, board: chess.Board) -> chess.Move:
        result = self.analyze_position(board)
        if result["best_move"] is None:
            raise RuntimeError("Stockfish returned no best move.")
        return result["best_move"]

    def close(self):
        if self._owns_engine and self.engine is not None:
            self.engine.close()
            self.engine = None
