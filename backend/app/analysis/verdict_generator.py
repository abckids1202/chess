"""Template-based dramatic verdicts based only on measured engine data."""

from __future__ import annotations

from typing import Any


def generate_verdict(summary: dict[str, Any]) -> str:
    turning = summary.get("turning_point")
    largest = float(turning.get("eval_loss", 0)) if turning else 0
    total_blunders = summary.get("white_blunders", 0) + summary.get("black_blunders", 0)
    total_mistakes = summary.get("white_mistakes", 0) + summary.get("black_mistakes", 0)
    result = summary.get("result", "*")
    if largest >= 5:
        return f"The game completely turned on move {turning['move_number']}."
    if result != "*" and total_blunders >= 2:
        return "You got the result, but the engine was not impressed."
    if total_blunders == 0 and total_mistakes <= 2:
        return "A relatively clean game with only minor inaccuracies."
    if total_blunders >= 2 or total_mistakes >= 6:
        return "A chaotic game where both sides had chances."
    if largest >= 3:
        return f"A balanced game collapsed after move {turning['move_number']}."
    return "The position stayed playable, but a few decisions shaped the final story."
