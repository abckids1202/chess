import chess

from backend.app.analysis.analysis_service import analyze_pgn
from backend.app.analysis.pgn_parser import PGNParseError, parse_pgn


class FakeAnalyzer:
    """Deterministic engine stand-in for analysis tests."""

    def analyze_position(self, board):
        move = next(iter(board.legal_moves), None)
        return {
            "score": {"type": "cp", "numeric": 0.0, "display": "+0.00"},
            "best_move": move,
            "pv": [move.uci()] if move else [],
        }


def test_parse_pgn_replays_mainline_and_records_fens():
    parsed = parse_pgn('[Event "Test"]\n[Result "*"]\n\n1. e4 e5 2. Nf3 *')

    assert parsed["headers"]["Event"] == "Test"
    assert len(parsed["moves"]) == 3
    assert parsed["moves"][0]["san"] == "e4"
    assert parsed["moves"][0]["fen_before"] == chess.STARTING_FEN
    assert parsed["moves"][-1]["fen_after"].split()[1] == "b"


def test_parse_pgn_rejects_empty_and_illegal_games():
    for pgn in ("", "1. e5 *"):
        try:
            parse_pgn(pgn)
        except PGNParseError:
            pass
        else:
            raise AssertionError("invalid PGN was accepted")


def test_analysis_report_contains_timeline_and_summary():
    report = analyze_pgn(
        '[Event "Test"]\n[Date "2026.01.01"]\n[White "A"]\n[Black "B"]\n[Result "1-0"]\n\n1. e4 e5 2. Nf3 1-0',
        FakeAnalyzer(),
    )

    assert report["game_info"] == {
        "white": "A",
        "black": "B",
        "result": "1-0",
        "date": "2026.01.01",
        "event": "Test",
        "white_elo": "",
        "black_elo": "",
    }
    assert report["summary"]["total_moves"] == 3
    assert report["summary"]["verdict"]
    assert len(report["moves"]) == len(report["evaluation_timeline"]) == 3
    assert {"best_move_san", "classification", "eval_loss"} <= report["moves"][0].keys()
