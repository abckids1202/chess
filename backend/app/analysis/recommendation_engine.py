"""Cautious practice recommendations derived from analysis evidence."""

from __future__ import annotations

from typing import Any


def recommendations(moves: list[dict[str, Any]], result: str) -> list[str]:
    suggestions = []
    critical = [move for move in moves if move["classification"] in {"critical", "blunder"}]
    if critical:
        suggestions.append("Tactical puzzles")
    if any(move["played_move_san"].startswith("Q") for move in critical):
        suggestions.append("Queen safety")
    if any(move["after_score"].get("type") == "mate" for move in critical):
        suggestions.append("King safety and checkmate defense")
    if any(move["ply"] <= 20 for move in critical):
        suggestions.append("Opening principles")
    if result in {"1-0", "0-1"} and critical:
        suggestions.append("Converting winning positions")
    if not suggestions:
        suggestions.append("Keep reviewing precise endgame decisions")
    return list(dict.fromkeys(suggestions))[:4]


def diagnose_style(moves: list[dict[str, Any]]) -> str:
    if not moves:
        return "This game does not contain enough moves for a style diagnosis."
    checks = sum("+" in move["played_move_san"] or "#" in move["played_move_san"] for move in moves)
    captures = sum("x" in move["played_move_san"] for move in moves)
    queen_moves = sum(move["played_move_san"].startswith("Q") for move in moves)
    blunders = sum(move["classification"] in {"blunder", "critical"} for move in moves)
    if blunders >= 3:
        return "This game suggests a chaotic style with several tactical swings."
    if checks >= 4 and captures >= 4:
        return "This game suggests an aggressive, tactical approach."
    if queen_moves >= 5:
        return "This game suggests a queen-dependent approach; develop the rest of the army first."
    return "This game suggests a balanced approach with room for sharper tactical decisions."
