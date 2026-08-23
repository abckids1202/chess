"""Print top legal policy moves for several rating conditions."""

from __future__ import annotations

import argparse

import chess

from ml.bot.inference import HumanPolicyBot


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--fen", required=True)
    parser.add_argument("--ratings", nargs="+", type=int, default=[700, 1000, 1300, 1600, 1900, 2200])
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    board = chess.Board(args.fen)
    print(f"POSITION: {board.fen()}")
    for rating in args.ratings:
        bot = HumanPolicyBot(args.model, rating=rating, deterministic=True)
        moves = bot.predict_top_moves(board, limit=args.limit)
        print(f"\n{rating}:")
        for move, prob in moves:
            print(f"  {board.san(move):8s} {prob:.2%} {move.uci()}")


if __name__ == "__main__":
    main()
