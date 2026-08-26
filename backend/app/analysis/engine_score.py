"""Convert python-chess engine scores into white-centric UI values."""

from __future__ import annotations

from typing import Any, Optional

import chess


def score_to_data(score: Any) -> dict[str, Any]:
    if score is None:
        return {"type": "cp", "numeric": 0.0, "display": "0.00"}
    if hasattr(score, "pov"):
        score = score.pov(chess.WHITE)
    mate = score.mate() if hasattr(score, "mate") else None
    if mate is not None:
        numeric = 100.0 if mate > 0 else -100.0
        return {
            "type": "mate",
            "mate_in": mate,
            "numeric": numeric,
            "display": f"Mate in {abs(mate)}" if mate > 0 else f"Mated in {abs(mate)}",
        }
    centipawns = score.score(mate_score=10000) if hasattr(score, "score") else 0
    numeric = max(-100.0, min(100.0, (centipawns or 0) / 100.0))
    return {"type": "cp", "numeric": round(numeric, 2), "display": f"{numeric:+.2f}"}


def score_from_info(info: dict[str, Any]) -> dict[str, Any]:
    return score_to_data(info.get("score"))


def is_forced_mate(score: Optional[dict[str, Any]]) -> bool:
    return bool(score and score.get("type") == "mate")
