"""Normalize and validate Lichess-style puzzle records."""

from __future__ import annotations

from typing import Any

import chess


def normalize_record(record: dict[str, Any]) -> dict[str, Any]:
    puzzle_id = str(record.get("id") or record.get("PuzzleId") or "")
    source_fen = str(record.get("fen") or record.get("FEN") or "")
    moves_value = record.get("moves_uci") or record.get("Moves") or []
    moves = moves_value.split() if isinstance(moves_value, str) else list(moves_value)
    if not puzzle_id or not source_fen or len(moves) < 2:
        raise ValueError("puzzle requires an id, FEN, and trigger plus solution moves")

    board = chess.Board(source_fen)
    trigger = chess.Move.from_uci(moves[0])
    if trigger not in board.legal_moves:
        raise ValueError(f"illegal trigger move: {moves[0]}")
    board.push(trigger)
    solver_fen = board.fen()
    solution_moves: list[str] = []
    for index, move_uci in enumerate(moves[1:], start=1):
        move = chess.Move.from_uci(move_uci)
        if move not in board.legal_moves:
            raise ValueError(f"illegal move at sequence index {index}: {move_uci}")
        solution_moves.append(move.uci())
        board.push(move)

    themes = record.get("themes") or record.get("Themes") or []
    if isinstance(themes, str):
        themes = themes.replace(",", " ").split()
    opening_tags = record.get("opening_tags") or record.get("OpeningTags") or []
    if isinstance(opening_tags, str):
        opening_tags = opening_tags.replace(",", " ").split()

    normalized_themes = sorted(set(str(theme) for theme in themes))

    rating = record.get("rating") or record.get("Rating")
    return {
        "id": puzzle_id,
        "title": str(record.get("title") or f"Lichess puzzle {puzzle_id}"),
        "source_fen": source_fen,
        "solver_fen": solver_fen,
        "trigger_move": trigger.uci(),
        "solution_moves": solution_moves,
        "rating": int(rating) if rating not in (None, "", "?") else None,
        "themes": normalized_themes,
        "category": normalized_themes[0] if normalized_themes else "uncategorized",
        "hint": "Look for a forcing move: check, capture, or threat.",
        "explanation": "Imported from the validated Lichess puzzle dataset.",
        "opening_tags": sorted(set(str(tag) for tag in opening_tags)),
        "is_checkmate": board.is_checkmate(),
    }


def validate_normalized(record: dict[str, Any]) -> tuple[bool, str]:
    try:
        board = chess.Board(record["solver_fen"])
        for move_uci in record["solution_moves"]:
            move = chess.Move.from_uci(move_uci)
            if move not in board.legal_moves:
                return False, f"illegal solution move: {move_uci}"
            board.push(move)
    except (KeyError, ValueError) as exc:
        return False, str(exc)
    if record.get("is_checkmate") is True and not board.is_checkmate():
        return False, "checkmate label does not match final board"
    return True, "valid"
