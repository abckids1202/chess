"""Gameplay state machine for normalized multi-move puzzles."""

from __future__ import annotations

import chess


class PuzzleSession:
    def __init__(self, puzzle: dict):
        self.puzzle = puzzle
        self.board = chess.Board(puzzle["solver_fen"])
        self.step = 0
        self.attempts = 0

    @property
    def complete(self) -> bool:
        return self.step >= len(self.puzzle["solution_moves"])

    @property
    def waiting_for_player(self) -> bool:
        return not self.complete and self.step % 2 == 0

    def submit_player_move(self, move_uci: str) -> dict:
        self.attempts += 1
        if not self.waiting_for_player:
            return {"ok": False, "reason": "waiting_for_reply"}
        expected = self.puzzle["solution_moves"][self.step]
        if move_uci != expected:
            return {"ok": False, "reason": "wrong_move", "expected": expected}
        self._push(move_uci)
        return {"ok": True, "complete": self.complete, "move": move_uci}

    def play_forced_reply(self) -> str | None:
        if self.complete or self.waiting_for_player:
            return None
        move_uci = self.puzzle["solution_moves"][self.step]
        self._push(move_uci)
        return move_uci

    def hint(self) -> str | None:
        if not self.waiting_for_player:
            return None
        return self.puzzle["solution_moves"][self.step]

    def _push(self, move_uci: str):
        move = chess.Move.from_uci(move_uci)
        if move not in self.board.legal_moves:
            raise ValueError(f"invalid normalized puzzle move: {move_uci}")
        self.board.push(move)
        self.step += 1
