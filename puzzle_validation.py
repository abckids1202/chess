"""Convenience import for puzzle validation scripts."""

from backend.app.puzzle_validation import validate_puzzle

__all__ = ["validate_puzzle"]


if __name__ == "__main__":
    valid, message = validate_puzzle(
        chess.STARTING_FEN,
        ["e2e4", "e7e5", "g1f3"],
    )
    print(valid, message)
