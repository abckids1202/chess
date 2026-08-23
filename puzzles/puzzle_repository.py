"""Read only repository for normalized puzzle JSON."""

from __future__ import annotations

import json
from pathlib import Path

from .puzzle_validator import validate_normalized


class PuzzleRepository:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        records = json.loads(self.path.read_text(encoding="utf-8"))
        self.puzzles = []
        for record in records:
            valid, _message = validate_normalized(record)
            if valid:
                self.puzzles.append(record)

    def all(self) -> list[dict]:
        return list(self.puzzles)

    def by_theme(self, theme: str) -> list[dict]:
        return [puzzle for puzzle in self.puzzles if theme in puzzle.get("themes", [])]
