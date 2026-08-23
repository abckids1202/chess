"""Clean inference API for rating-conditioned human policy bots."""

from __future__ import annotations

import json
from pathlib import Path

import chess
import numpy as np

from ml.common.board_encoder import BOARD_ENCODER_VERSION, encode_board
from ml.common.move_encoder import MOVE_VOCAB_VERSION, build_legal_move_mask, decode_move


class HumanPolicyBot:
    def __init__(
        self,
        model_path: str | Path,
        rating: int,
        temperature: float = 0.9,
        deterministic: bool = False,
        top_k: int | None = None,
        device: str | None = None,
    ):
        import torch

        from ml.bot.policy_model import HumanPolicyNet

        self.torch = torch
        self.rating = rating
        self.temperature = temperature
        self.deterministic = deterministic
        self.top_k = top_k
        self.device = torch.device(device or ("cuda" if torch.cuda.is_available() else "cpu"))
        self.model_path = Path(model_path)
        self.metadata = self._load_metadata()
        self._validate_metadata()
        self.model = HumanPolicyNet(**self.metadata.get("architecture", {})).to(self.device)
        checkpoint = torch.load(self.model_path, map_location=self.device)
        state_dict = checkpoint.get("model_state_dict", checkpoint)
        self.model.load_state_dict(state_dict)
        self.model.eval()

    def choose_move(self, board: chess.Board) -> chess.Move:
        top_moves = self.predict_top_moves(board, limit=1)
        if not top_moves:
            raise ValueError("no legal moves available")
        return top_moves[0][0]

    def predict_top_moves(self, board: chess.Board, limit: int = 5) -> list[tuple[chess.Move, float]]:
        torch = self.torch
        with torch.no_grad():
            board_tensor = torch.from_numpy(encode_board(board)).unsqueeze(0).to(self.device)
            rating_tensor = torch.tensor([self._normalize_rating(self.rating)], dtype=torch.float32, device=self.device)
            logits = self.model(board_tensor, rating_tensor).squeeze(0)
            logits = logits + build_legal_move_mask(board).to(self.device)
            logits = logits / max(self.temperature, 1e-6)
            if self.top_k is not None:
                values, indices = torch.topk(logits, min(self.top_k, logits.numel()))
                filtered = torch.full_like(logits, float("-inf"))
                filtered[indices] = values
                logits = filtered
            probs = torch.softmax(logits, dim=0)
            if self.deterministic:
                chosen = torch.argmax(probs).view(1)
            else:
                chosen = torch.multinomial(probs, num_samples=min(limit, int((probs > 0).sum().item())), replacement=False)
            return [(decode_move(int(index)), float(probs[index].item())) for index in chosen[:limit]]

    def _normalize_rating(self, rating: int) -> float:
        mean = self.metadata.get("rating_mean", 1500.0)
        std = self.metadata.get("rating_std", 400.0)
        return (rating - mean) / max(std, 1.0)

    def _load_metadata(self) -> dict:
        metadata_path = self.model_path.with_suffix(".json")
        if not metadata_path.exists():
            return {}
        return json.loads(metadata_path.read_text(encoding="utf-8"))

    def _validate_metadata(self) -> None:
        if self.metadata.get("board_encoder_version", BOARD_ENCODER_VERSION) != BOARD_ENCODER_VERSION:
            raise ValueError("model board encoder version does not match code")
        if self.metadata.get("move_vocab_version", MOVE_VOCAB_VERSION) != MOVE_VOCAB_VERSION:
            raise ValueError("model move vocabulary version does not match code")
