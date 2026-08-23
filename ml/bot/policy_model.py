"""Rating-conditioned human policy model for CHESS V2."""

from __future__ import annotations

try:
    import torch
    from torch import nn
except ImportError:  # pragma: no cover
    torch = None
    nn = None

from ml.common.move_encoder import NUM_MOVES


if nn is not None:
    from ml.common.chess_encoder import ChessEncoder


    class RatingMLP(nn.Module):
        def __init__(self, embedding_dim: int = 32):
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(1, 32),
                nn.SiLU(),
                nn.Linear(32, embedding_dim),
                nn.SiLU(),
            )

        def forward(self, rating):
            return self.net(rating.view(-1, 1).float())


    class HumanPolicyNet(nn.Module):
        """Predicts human move distributions from board state and rating."""

        def __init__(
            self,
            channels: int = 96,
            residual_blocks: int = 6,
            embedding_dim: int = 256,
            rating_embedding_dim: int = 32,
            hidden_dim: int = 512,
            dropout: float = 0.1,
            num_moves: int = NUM_MOVES,
        ):
            super().__init__()
            self.board_encoder = ChessEncoder(
                channels=channels,
                residual_blocks=residual_blocks,
                embedding_dim=embedding_dim,
                dropout=dropout,
            )
            self.rating_encoder = RatingMLP(rating_embedding_dim)
            self.policy_head = nn.Sequential(
                nn.Linear(embedding_dim + rating_embedding_dim, hidden_dim),
                nn.SiLU(),
                nn.Dropout(dropout),
                nn.Linear(hidden_dim, num_moves),
            )

        def forward(self, board_tensor, rating_tensor):
            board_embedding = self.board_encoder(board_tensor)
            rating_embedding = self.rating_encoder(rating_tensor)
            return self.policy_head(torch.cat([board_embedding, rating_embedding], dim=1))
