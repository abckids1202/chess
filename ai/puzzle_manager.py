"""Runtime puzzle manager placeholder for generated-puzzle integration."""

from __future__ import annotations

import chess


class PuzzleManager:
    def __init__(self, puzzle: dict | None = None):
        self.puzzle = puzzle
        self.board = chess.Board(puzzle["start_fen"]) if puzzle else None
        self.step = 0

    def load_puzzle(self, puzzle: dict):
        self.puzzle = puzzle
        self.board = chess.Board(puzzle["start_fen"])
        self.step = 0

    def check_player_move(self, move_uci: str) -> bool:
        self._require_puzzle()
        expected = self.puzzle["moves_uci"][self.step]
        if move_uci != expected:
            return False
        self.board.push(chess.Move.from_uci(move_uci))
        self.step += 1
        return True

    def get_forced_reply(self) -> str | None:
        self._require_puzzle()
        if self.step >= len(self.puzzle["moves_uci"]):
            return None
        move_uci = self.puzzle["moves_uci"][self.step]
        self.board.push(chess.Move.from_uci(move_uci))
        self.step += 1
        return move_uci

    def is_complete(self) -> bool:
        return bool(self.puzzle and self.step >= len(self.puzzle["moves_uci"]))

    def get_hint(self) -> str:
        self._require_puzzle()
        return self.puzzle.get("hint", "")

    def _require_puzzle(self):
        if not self.puzzle or self.board is None:
            raise RuntimeError("no puzzle loaded")
