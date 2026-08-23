"""Import JSON/JSONL/CSV Lichess puzzle records into normalized JSON."""

from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path
from typing import Iterable

from .puzzle_validator import normalize_record


def read_records(path: str | Path) -> Iterable[dict]:
    path = Path(path)
    if path.name.lower().endswith(".csv.zst"):
        import zstandard as zstd

        with path.open("rb") as compressed:
            with zstd.ZstdDecompressor().stream_reader(compressed) as reader:
                with io.TextIOWrapper(reader, encoding="utf-8-sig", errors="replace") as handle:
                    yield from csv.DictReader(handle)
        return
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            yield from csv.DictReader(handle)
        return
    if path.suffix.lower() == ".jsonl":
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    yield json.loads(line)
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    yield from (data if isinstance(data, list) else [data])


def import_puzzles(input_path: str | Path, output_path: str | Path, limit: int | None = None) -> int:
    normalized = []
    rejected = 0
    for record in read_records(input_path):
        if limit is not None and len(normalized) >= limit:
            break
        try:
            normalized.append(normalize_record(record))
        except (ValueError, TypeError):
            rejected += 1
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(json.dumps(normalized, indent=2), encoding="utf-8")
    print(f"accepted={len(normalized)} rejected={rejected}")
    return len(normalized)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    import_puzzles(args.input, args.output, limit=args.limit)


if __name__ == "__main__":
    main()
