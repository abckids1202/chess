"""Orchestrate PGN replay, Stockfish comparisons, and report generation."""

from __future__ import annotations

from typing import Any

import chess

from .engine_score import is_forced_mate
from .move_classifier import classify_move, evaluation_loss, move_commentary
from .pgn_parser import parse_pgn
from .recommendation_engine import diagnose_style, recommendations
from .stockfish_analyzer import StockfishAnalyzer
from .verdict_generator import generate_verdict


def _player_impact(move: dict[str, Any]) -> float:
    before = move["eval_before"]
    after = move["eval_after"]
    return after - before if move["color"] == "white" else before - after


def analyze_pgn(
    pgn_text: str,
    analyzer: StockfishAnalyzer,
    max_plies: int = 120,
) -> dict[str, Any]:
    parsed = parse_pgn(pgn_text, max_plies=max_plies)
    analyzed_moves = []
    for parsed_move in parsed["moves"]:
        board = chess.Board(parsed_move["fen_before"])
        engine_result = analyzer.analyze_position(board)
        best_move = engine_result["best_move"]
        if best_move is None:
            raise RuntimeError("Stockfish returned no best move for this position.")
        best_san = board.san(best_move)
        best_board = board.copy(stack=False)
        best_board.push(best_move)
        best_result = analyzer.analyze_position(best_board)
        played_move = chess.Move.from_uci(parsed_move["uci"])
        played_board = board.copy(stack=False)
        played_board.push(played_move)
        played_result = analyzer.analyze_position(played_board)
        before_score = engine_result["score"]
        best_after_score = best_result["score"]
        after_score = played_result["score"]
        loss = evaluation_loss(
            parsed_move["color"],
            best_after_score["numeric"],
            after_score["numeric"],
        )
        best_is_mate = is_forced_mate(best_after_score)
        played_is_opponent_mate = is_forced_mate(after_score) and (
            (parsed_move["color"] == "white" and after_score["numeric"] <= -100.0)
            or (parsed_move["color"] == "black" and after_score["numeric"] >= 100.0)
        )
        same_best = parsed_move["uci"] == best_move.uci()
        classification = classify_move(
            loss,
            best_is_mate=best_is_mate,
            played_is_opponent_mate=played_is_opponent_mate,
            is_best_move=same_best,
        )
        analyzed_moves.append({
            **parsed_move,
            "played_move_uci": parsed_move["uci"],
            "played_move_san": parsed_move["san"],
            "best_move_uci": best_move.uci(),
            "best_move_san": best_san,
            "eval_before": before_score["numeric"],
            "eval_after": after_score["numeric"],
            "eval_before_display": before_score["display"],
            "eval_after_display": after_score["display"],
            "before_score": before_score,
            "best_after_score": best_after_score,
            "after_score": after_score,
            "eval_loss": loss,
            "classification": classification,
            "principal_variation": engine_result["pv"],
            "commentary": move_commentary(classification, loss, best_san),
            "best_move": same_best,
        })

    critical = sorted(
        [move for move in analyzed_moves if move["eval_loss"] >= 0.8],
        key=lambda move: move["eval_loss"],
        reverse=True,
    )[:5]
    turning = critical[0] if critical else max(analyzed_moves, key=lambda move: move["eval_loss"])
    white_moves = [move for move in analyzed_moves if move["color"] == "white"]
    black_moves = [move for move in analyzed_moves if move["color"] == "black"]

    def accuracy(moves: list[dict[str, Any]]) -> float:
        if not moves:
            return 0.0
        average_loss = sum(move["eval_loss"] for move in moves) / len(moves)
        return round(max(0.0, min(100.0, 100.0 - average_loss * 20.0)), 1)

    summary = {
        "result": parsed["result"],
        "total_moves": len(analyzed_moves),
        "accuracy_white": accuracy(white_moves),
        "accuracy_black": accuracy(black_moves),
        "white_blunders": sum(move["classification"] in {"blunder", "critical"} for move in white_moves),
        "black_blunders": sum(move["classification"] in {"blunder", "critical"} for move in black_moves),
        "white_mistakes": sum(move["classification"] == "mistake" for move in white_moves),
        "black_mistakes": sum(move["classification"] == "mistake" for move in black_moves),
        "turning_point": turning,
        "best_move": max(analyzed_moves, key=_player_impact),
        "worst_move": max(analyzed_moves, key=lambda move: move["eval_loss"]),
        "chaos_meter": round(min(100, sum(min(move["eval_loss"], 5) for move in analyzed_moves) / max(1, len(analyzed_moves)) * 25)),
        "practice_recommendations": recommendations(analyzed_moves, parsed["result"]),
        "player_diagnosis": diagnose_style(analyzed_moves),
    }
    summary["verdict"] = generate_verdict(summary)
    return {
        "game_info": {
            "white": parsed["headers"].get("White", "White"),
            "black": parsed["headers"].get("Black", "Black"),
            "result": parsed["result"],
            "date": parsed["headers"].get("Date", ""),
            "event": parsed["headers"].get("Event", ""),
            "white_elo": parsed["headers"].get("WhiteElo", ""),
            "black_elo": parsed["headers"].get("BlackElo", ""),
        },
        "summary": summary,
        "moves": analyzed_moves,
        "critical_moments": critical,
        "evaluation_timeline": [
            {
                "ply": move["ply"],
                "move_number": move["move_number"],
                "color": move["color"],
                "eval_after": move["eval_after"],
                "display": move["eval_after_display"],
                "classification": move["classification"],
            }
            for move in analyzed_moves
        ],
        "truncated": parsed["truncated"],
    }
