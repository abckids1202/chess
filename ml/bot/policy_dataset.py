"""Parquet-backed policy dataset.

The first training version keeps FEN in shards for transparency and encodes
boards at load time. Later, if FEN parsing becomes the bottleneck, we can store
pre-encoded uint8 planes in the shards without changing the model interface.
"""

from __future__ import annotations

from pathlib import Path

import chess
import numpy as np

from ml.common.board_encoder import encode_board


class PolicyParquetDataset:
    def __init__(self, shard_dir: str | Path, rating_mean: float = 1500.0, rating_std: float = 400.0):
        import pyarrow.parquet as pq

        self.shard_dir = Path(shard_dir)
        self.files = sorted(self.shard_dir.glob("*.parquet"))
        if not self.files:
            raise FileNotFoundError(f"no parquet shards found in {self.shard_dir}")
        self.tables = [pq.read_table(path, columns=["fen", "player_rating", "move_index"]) for path in self.files]
        self.offsets = []
        total = 0
        for table in self.tables:
            self.offsets.append(total)
            total += table.num_rows
        self.total = total
        self.rating_mean = rating_mean
        self.rating_std = max(rating_std, 1.0)

    def __len__(self):
        return self.total

    def __getitem__(self, index):
        table_index = max(i for i, offset in enumerate(self.offsets) if offset <= index)
        local_index = index - self.offsets[table_index]
        row = self.tables[table_index].slice(local_index, 1).to_pylist()[0]
        board = chess.Board(row["fen"])
        board_tensor = encode_board(board)
        rating = np.array([(row["player_rating"] - self.rating_mean) / self.rating_std], dtype=np.float32)
        return board_tensor, rating[0], int(row["move_index"])
