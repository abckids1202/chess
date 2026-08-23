"""Memory-safe PGN streaming utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator, TextIO

import chess.pgn


def open_text_stream(path: str | Path) -> TextIO:
    path = Path(path)
    if path.suffix.lower() == ".zst":
        import zstandard as zstd

        compressed = path.open("rb")
        reader = zstd.ZstdDecompressor().stream_reader(compressed)
        import io

        return io.TextIOWrapper(reader, encoding="utf-8", errors="replace")
    return path.open("r", encoding="utf-8", errors="replace")


def stream_games(path: str | Path) -> Iterator[chess.pgn.Game]:
    """Yield games one at a time from .pgn or .pgn.zst without loading all data."""

    with open_text_stream(path) as handle:
        while True:
            game = chess.pgn.read_game(handle)
            if game is None:
                break
            yield game


def parse_rating(value: str | None) -> int | None:
    try:
        return int(value) if value and value != "?" else None
    except ValueError:
        return None
