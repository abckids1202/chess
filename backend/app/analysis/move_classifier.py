"""Classify engine evaluation loss into readable Chess V2 labels."""

from __future__ import annotations


def evaluation_loss(color: str, best_after: float, played_after: float) -> float:
    # Scores are white-centric. Reverse the subtraction for Black so both
    # players are measured by how much worse their move made their game.
    loss = best_after - played_after if color == "white" else played_after - best_after
    return round(max(0.0, loss), 2)


def classify_move(
    loss: float,
    *,
    best_is_mate: bool = False,
    played_is_opponent_mate: bool = False,
    is_best_move: bool = False,
) -> str:
    if best_is_mate and played_is_opponent_mate:
        return "critical"
    if played_is_opponent_mate:
        return "critical"
    if is_best_move or loss <= 0.1:
        return "best"
    if loss <= 0.3:
        return "good"
    if loss <= 0.8:
        return "inaccuracy"
    if loss <= 3.0:
        return "mistake"
    return "blunder"


def move_commentary(classification: str, loss: float, best_san: str) -> str:
    if classification == "critical":
        return "This move allowed a forced tactical collapse."
    if classification == "blunder":
        return f"The position lost about {loss:.1f} pawns. The engine preferred {best_san}."
    if classification == "mistake":
        return f"This gave away a meaningful part of the position. Consider {best_san}."
    if classification == "inaccuracy":
        return f"A playable move, but {best_san} kept more pressure."
    if classification == "best":
        return "A precise choice that stayed close to the engine line."
    return "A solid move with only a small evaluation drift."
