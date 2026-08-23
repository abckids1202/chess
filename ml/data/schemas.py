"""Dataset schema constants and metadata helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone


@dataclass
class DatasetMetadata:
    dataset_name: str
    encoder_version: int
    move_vocab_version: int
    source_filename: str
    games_processed: int = 0
    positions_processed: int = 0
    samples_accepted: int = 0
    samples_rejected: int = 0
    rating_min: int | None = None
    rating_max: int | None = None
    created_at: str = ""

    def to_dict(self) -> dict:
        data = asdict(self)
        data["created_at"] = data["created_at"] or datetime.now(timezone.utc).isoformat()
        return data
