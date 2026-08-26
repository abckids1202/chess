"""Repositories and stats for local Chess V2 players and game events."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any, Optional

from .database import get_connection, row_to_dict


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _clean_username(username: str) -> str:
    value = (username or "").strip()
    if not value or len(value) > 24:
        raise ValueError("Username must be 1-24 characters")
    return value


def create_player(username: str) -> dict[str, Any]:
    username = _clean_username(username)
    now = _now()
    with get_connection() as conn:
        try:
            cur = conn.execute(
                """
                INSERT INTO players
                    (username, display_name, created_at, updated_at, last_active_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (username, username, now, now, now),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("That username already exists") from exc
        conn.execute(
            "UPDATE active_profile SET player_id = ?, updated_at = ? WHERE id = 1",
            (cur.lastrowid, now),
        )
        conn.execute("UPDATE local_profile SET username = ? WHERE id = 1", (username,))
        conn.commit()
        return row_to_dict(conn.execute("SELECT * FROM players WHERE id = ?", (cur.lastrowid,)).fetchone())


def get_player(player_id: int) -> Optional[dict[str, Any]]:
    with get_connection() as conn:
        return row_to_dict(conn.execute("SELECT * FROM players WHERE id = ?", (player_id,)).fetchone())


def get_all_players() -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM players ORDER BY COALESCE(last_active_at, updated_at, created_at) DESC, id"
        ).fetchall()
    return [row_to_dict(row) for row in rows]


def update_player(player_id: int, username: str) -> dict[str, Any]:
    username = _clean_username(username)
    now = _now()
    with get_connection() as conn:
        if conn.execute("SELECT 1 FROM players WHERE id = ?", (player_id,)).fetchone() is None:
            raise ValueError("Player not found")
        try:
            conn.execute(
                "UPDATE players SET username = ?, updated_at = ? WHERE id = ?",
                (username, now, player_id),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("That username already exists") from exc
        conn.execute("UPDATE local_profile SET username = ? WHERE id = 1", (username,))
        conn.commit()
        return row_to_dict(conn.execute("SELECT * FROM players WHERE id = ?", (player_id,)).fetchone())


def set_active_player(player_id: int) -> dict[str, Any]:
    now = _now()
    with get_connection() as conn:
        if conn.execute("SELECT 1 FROM players WHERE id = ?", (player_id,)).fetchone() is None:
            raise ValueError("Player not found")
        conn.execute("UPDATE players SET last_active_at = ? WHERE id = ?", (now, player_id))
        conn.execute(
            """
            INSERT INTO active_profile (id, player_id, updated_at) VALUES (1, ?, ?)
            ON CONFLICT(id) DO UPDATE SET player_id = excluded.player_id, updated_at = excluded.updated_at
            """,
            (player_id, now),
        )
        conn.execute("UPDATE local_profile SET username = ? WHERE id = 1", (row_username(conn, player_id),))
        conn.commit()
        return row_to_dict(conn.execute("SELECT * FROM players WHERE id = ?", (player_id,)).fetchone())


def get_active_player() -> dict[str, Any]:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT players.*
            FROM active_profile
            JOIN players ON players.id = active_profile.player_id
            WHERE active_profile.id = 1
            """
        ).fetchone()
        if row is None:
            row = conn.execute(
                "SELECT * FROM players ORDER BY COALESCE(last_active_at, updated_at, created_at) DESC, id LIMIT 1"
            ).fetchone()
            if row is not None:
                now = _now()
                conn.execute(
                    "INSERT OR REPLACE INTO active_profile (id, player_id, updated_at) VALUES (1, ?, ?)",
                    (row["id"], now),
                )
                conn.commit()
    if row is None:
        raise RuntimeError("No local player exists")
    return row_to_dict(row)


def row_username(conn: Any, player_id: int) -> str:
    row = conn.execute("SELECT username FROM players WHERE id = ?", (player_id,)).fetchone()
    return row["username"] if row else "Player"


def set_setting(player_id: int, key: str, value: Any) -> None:
    if not key.strip():
        raise ValueError("Setting key is required")
    encoded = json.dumps(value) if not isinstance(value, str) else value
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO player_settings (player_id, setting_key, setting_value)
            VALUES (?, ?, ?)
            ON CONFLICT(player_id, setting_key) DO UPDATE SET setting_value = excluded.setting_value
            """,
            (player_id, key.strip(), encoded),
        )
        conn.commit()


def get_all_settings(player_id: int) -> dict[str, Any]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT setting_key, setting_value FROM player_settings WHERE player_id = ?",
            (player_id,),
        ).fetchall()
    values: dict[str, Any] = {}
    for row in rows:
        try:
            values[row["setting_key"]] = json.loads(row["setting_value"])
        except (TypeError, json.JSONDecodeError):
            values[row["setting_key"]] = row["setting_value"]
    return values


def _game_result(game: dict[str, Any], player: dict[str, Any]) -> str:
    result = game.get("result") or "*"
    if result == "*":
        return "unfinished"
    if result == "1/2-1/2":
        return "draw"
    color = game.get("player_color")
    if color == "white" or (not color and game.get("white_name") == player["username"]):
        return "win" if result == "1-0" else "loss"
    return "win" if result == "0-1" else "loss"


def _decorate_game(row: Any, player: dict[str, Any]) -> dict[str, Any]:
    game = row_to_dict(row) if not isinstance(row, dict) else dict(row)
    game["player_result"] = _game_result(game, player)
    if game.get("opponent_name"):
        game["opponent_display"] = game["opponent_name"]
    elif game.get("player_color") == "white":
        game["opponent_display"] = game.get("black_name")
    else:
        game["opponent_display"] = game.get("white_name")
    game["date"] = game.get("ended_at") or game.get("created_at")
    return game


def get_recent_games(player_id: int, limit: int = 10) -> list[dict[str, Any]]:
    player = get_player(player_id)
    if not player:
        return []
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM local_games
            WHERE player_id = ? AND COALESCE(result, '*') <> '*'
            ORDER BY COALESCE(ended_at, created_at) DESC, id DESC
            LIMIT ?
            """,
            (player_id, limit),
        ).fetchall()
    return [_decorate_game(row, player) for row in rows]


def get_recent_puzzle_attempts(player_id: int, limit: int = 10) -> list[dict[str, Any]]:
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT * FROM local_puzzle_attempts
            WHERE player_id = ?
            ORDER BY COALESCE(attempted_at, created_at) DESC, id DESC
            LIMIT ?
            """,
            (player_id, limit),
        ).fetchall()
    attempts = []
    for row in rows:
        item = row_to_dict(row)
        try:
            item["themes"] = json.loads(item.get("themes") or "[]")
        except (TypeError, json.JSONDecodeError):
            item["themes"] = []
        item["solved"] = bool(item.get("correct"))
        item["date"] = item.get("attempted_at") or item.get("created_at")
        attempts.append(item)
    return attempts


def get_player_stats(player_id: int) -> dict[str, Any]:
    player = get_player(player_id)
    if not player:
        raise ValueError("Player not found")
    with get_connection() as conn:
        games = [row_to_dict(row) for row in conn.execute(
            "SELECT * FROM local_games WHERE player_id = ?", (player_id,)
        ).fetchall()]
        attempts = [row_to_dict(row) for row in conn.execute(
            "SELECT * FROM local_puzzle_attempts WHERE player_id = ?", (player_id,)
        ).fetchall()]

    completed = [game for game in games if (game.get("result") or "*") != "*"]
    results = [_game_result(game, player) for game in completed]
    wins = results.count("win")
    losses = results.count("loss")
    draws = results.count("draw")
    bot_games = [game for game in completed if game.get("mode") == "bot"]
    bot_results = [_game_result(game, player) for game in bot_games]
    bot_rank = {"stockfish easy": 1, "stockfish normal": 2, "stockfish hard": 3, "stockfish boss": 4}
    beaten_bots = [
        game.get("opponent_name")
        for game in bot_games
        if _game_result(game, player) == "win" and game.get("opponent_name")
    ]
    best_bot = max(beaten_bots, key=lambda name: bot_rank.get(name.lower(), 0), default=None)
    solved = sum(1 for attempt in attempts if attempt.get("correct"))
    ratings = [
        int(attempt["puzzle_rating"])
        for attempt in attempts
        if attempt.get("correct") and attempt.get("puzzle_rating") is not None
    ]
    attempts_count = len(attempts)
    return {
        "games_played": len(completed),
        "unfinished_games": len(games) - len(completed),
        "wins": wins,
        "losses": losses,
        "draws": draws,
        "win_rate": round(wins / len(completed), 3) if completed else 0,
        "bot_games": len(bot_games),
        "bot_wins": bot_results.count("win"),
        "bot_losses": bot_results.count("loss"),
        "bot_draws": bot_results.count("draw"),
        "best_bot_beaten": best_bot,
        "puzzle_attempts": attempts_count,
        "puzzles_solved": solved,
        "puzzle_accuracy": round(solved / attempts_count, 3) if attempts_count else 0,
        "average_puzzle_attempts": round(
            sum(max(1, int(attempt.get("attempts") or 1)) for attempt in attempts) / attempts_count, 2
        ) if attempts_count else 0,
        "best_puzzle_rating_solved": max(ratings) if ratings else None,
        "recent_games": get_recent_games(player_id),
        "recent_puzzles": get_recent_puzzle_attempts(player_id),
    }


def get_local_leaderboard() -> list[dict[str, Any]]:
    players = get_all_players()
    stats = [(player, get_player_stats(player["id"])) for player in players]
    categories = [
        ("Most games played", "games_played", False),
        ("Most wins", "wins", False),
        ("Most puzzle solves", "puzzles_solved", False),
        ("Best puzzle accuracy", "puzzle_accuracy", False),
    ]
    result = []
    for category, key, _ in categories:
        entries = sorted(
            [
                {
                    "player_id": player["id"],
                    "username": player["username"],
                    "score": round(stats[key] * 100, 1) if key == "puzzle_accuracy" else stats[key],
                }
                for player, stats in stats
            ],
            key=lambda item: item["score"],
            reverse=True,
        )
        result.append({"category": category, "entries": entries[:10]})
    return result
