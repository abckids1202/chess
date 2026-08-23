"""Manual Stockfish connection test.

Run from the project root with:

    python test_stockfish.py

Set STOCKFISH_PATH if the executable is stored somewhere else.
"""

import os

import chess

from stockfish_bot import StockfishBot


STOCKFISH_PATH = os.getenv(
    "STOCKFISH_PATH",
    r"C:\Users\charl\Downloads\stockfish-windows-x86-64-avx2\stockfish\stockfish-windows-x86-64-avx2.exe",
)


def main():
    board = chess.Board()
    bot = StockfishBot(STOCKFISH_PATH, skill_level=5, move_time=0.5)
    try:
        move = bot.choose_move(board)
        print("Stockfish move:", move.uci())
        print("SAN:", board.san(move))
    finally:
        bot.close()


if __name__ == "__main__":
    main()
