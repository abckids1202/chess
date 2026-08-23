"""Authoritative python-chess game controller for local games and services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import chess

from .pgn_utils import board_to_pgn


@dataclass(frozen=True)
class MoveRecord:
    ply: int
    uci: str
    san: str
    fen_after: str
    captured: Optional[str] = None


class GameController:
    """Own one authoritative board and all derived local-game state."""

    def __init__(self, fen: Optional[str] = None):
        self.start_fen = fen or chess.STARTING_FEN
        self.board = chess.Board(self.start_fen)
        self.records: list[MoveRecord] = []
        self.selected_square: Optional[chess.Square] = None
        self.captured: dict[bool, list[str]] = {chess.WHITE: [], chess.BLACK: []}
        self.result_override: Optional[str] = None

    @property
    def turn(self) -> bool:
        return self.board.turn

    @property
    def game_over(self) -> bool:
        return self.result_override is not None or self.board.is_game_over(claim_draw=True)

    @property
    def result(self) -> str:
        if self.result_override:
            return self.result_override
        return self.board.result(claim_draw=True) if self.board.is_game_over(claim_draw=True) else "*"

    def select(self, square_name: str) -> list[chess.Move]:
        square = chess.parse_square(square_name)
        piece = self.board.piece_at(square)
        if piece is None or piece.color != self.board.turn or self.game_over:
            self.selected_square = None
            return []
        self.selected_square = square
        return [move for move in self.board.legal_moves if move.from_square == square]

    def clear_selection(self):
        self.selected_square = None

    def legal_moves_for_selected(self) -> list[chess.Move]:
        if self.selected_square is None:
            return []
        return [move for move in self.board.legal_moves if move.from_square == self.selected_square]

    def push_uci(self, move_uci: str) -> MoveRecord:
        if self.game_over:
            raise ValueError("game is already over")
        move = chess.Move.from_uci(move_uci)
        if move not in self.board.legal_moves:
            raise ValueError(f"illegal move: {move_uci}")
        san = self.board.san(move)
        captured_piece = self.board.piece_at(move.to_square)
        if self.board.is_en_passant(move):
            captured_piece = chess.Piece(chess.PAWN, not self.board.turn)
        self.board.push(move)
        record = MoveRecord(
            ply=len(self.records),
            uci=move.uci(),
            san=san,
            fen_after=self.board.fen(),
            captured=captured_piece.symbol() if captured_piece else None,
        )
        self.records.append(record)
        if captured_piece:
            self.captured[not captured_piece.color].append(captured_piece.symbol())
        self.selected_square = None
        return record

    def undo(self) -> Optional[MoveRecord]:
        if not self.board.move_stack:
            return None
        move = self.board.pop()
        record = self.records.pop()
        if record.captured:
            captured = chess.Piece.from_symbol(record.captured)
            if self.captured[not captured.color]:
                self.captured[not captured.color].pop()
        self.selected_square = None
        return record

    def reset(self):
        self.__init__(self.start_fen)

    def resign(self, color: bool):
        self.result_override = "0-1" if color == chess.WHITE else "1-0"

    def fen(self) -> str:
        return self.board.fen()

    def pgn(self, *, headers: Optional[dict[str, str]] = None) -> str:
        return board_to_pgn(self.board, headers=headers)
