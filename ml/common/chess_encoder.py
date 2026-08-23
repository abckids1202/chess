"""Small reusable neural encoder blocks for CHESS V2 models."""

from __future__ import annotations

try:
    import torch
    from torch import nn
except ImportError:  # pragma: no cover
    torch = None
    nn = None


if nn is not None:
    class ResidualBlock(nn.Module):
        def __init__(self, channels: int, dropout: float = 0.0):
            super().__init__()
            self.net = nn.Sequential(
                nn.Conv2d(channels, channels, kernel_size=3, padding=1, bias=False),
                nn.BatchNorm2d(channels),
                nn.SiLU(),
                nn.Dropout2d(dropout),
                nn.Conv2d(channels, channels, kernel_size=3, padding=1, bias=False),
                nn.BatchNorm2d(channels),
            )
            self.activation = nn.SiLU()

        def forward(self, x):
            return self.activation(x + self.net(x))


    class ChessEncoder(nn.Module):
        """CNN encoder used by policy, puzzle, and value models."""

        def __init__(self, input_planes: int = 18, channels: int = 96, residual_blocks: int = 6, embedding_dim: int = 256, dropout: float = 0.1):
            super().__init__()
            self.stem = nn.Sequential(
                nn.Conv2d(input_planes, channels, kernel_size=3, padding=1, bias=False),
                nn.BatchNorm2d(channels),
                nn.SiLU(),
            )
            self.blocks = nn.Sequential(*[ResidualBlock(channels, dropout=dropout) for _ in range(residual_blocks)])
            self.head = nn.Sequential(
                nn.AdaptiveAvgPool2d(1),
                nn.Flatten(),
                nn.Linear(channels, embedding_dim),
                nn.SiLU(),
                nn.Dropout(dropout),
            )

        def forward(self, boards):
            return self.head(self.blocks(self.stem(boards)))
