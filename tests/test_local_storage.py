import backend.app.database as database
from backend.app.database import init_db
from backend.app.local_storage import create_player, get_active_player, get_game_history, set_active_player
from backend.app.main import (
    HTTPException,
    LocalGameCreate,
    LocalGameFinish,
    LocalMoveCreate,
    LocalPuzzleAttemptCreate,
    create_local_game,
    finish_local_game,
    delete_last_local_move,
    local_game_history,
    local_stats,
    save_local_move,
    save_local_puzzle_attempt,
)


def test_local_storage_revalidates_moves_with_python_chess():
    init_db()
    game = create_local_game(LocalGameCreate(mode="test"))
    saved = save_local_move(
        game["id"],
        LocalMoveCreate(ply=0, uci="e2e4", san="e4", fen_after="ignored"),
    )
    assert saved["uci"] == "e2e4"
    assert saved["fen_after"].split()[1] == "b"

    try:
        save_local_move(
            game["id"],
            LocalMoveCreate(ply=1, uci="e2e5", san="e5", fen_after="ignored"),
        )
    except HTTPException as exc:
        assert exc.status_code == 400
    else:
        raise AssertionError("backend accepted an illegal move")

    assert delete_last_local_move(game["id"])["deleted"] is True


def test_local_profiles_and_event_stats_are_separate(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DATA_DIR", tmp_path)
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "chess_v2.db")
    init_db()

    first = get_active_player()
    assert first["username"] == "Player"
    second = create_player("Matthew")
    assert get_active_player()["id"] == second["id"]

    set_active_player(first["id"])
    game = create_local_game(
        LocalGameCreate(white_name="Player", black_name="Stockfish Easy", mode="bot")
    )
    save_local_move(
        game["id"],
        LocalMoveCreate(ply=0, uci="e2e4", san="e4", fen_after="ignored"),
    )
    finish_local_game(
        game["id"],
        LocalGameFinish(
            result="1-0",
            result_reason="checkmate",
            pgn="1. e4 1-0",
            final_fen="final",
        ),
    )
    save_local_puzzle_attempt(
        LocalPuzzleAttemptCreate(
            puzzle_id="mate_001",
            puzzle_rating=950,
            themes=["mateIn1"],
            correct=True,
            attempts=1,
        )
    )

    stats = local_stats()
    assert stats["games_played"] == 1
    assert stats["wins"] == 1
    assert stats["bot_games"] == 1
    assert stats["bot_wins"] == 1
    assert stats["puzzles_solved"] == 1
    assert stats["best_puzzle_rating_solved"] == 950
    assert stats["recent_games"][0]["result_reason"] == "checkmate"
    assert stats["recent_puzzles"][0]["themes"] == ["mateIn1"]
    history = get_game_history(first["id"])
    assert history[0]["pgn"] == "1. e4 1-0"
    assert history[0]["player_result"] == "win"
    assert local_game_history(50)["games"][0]["pgn"] == "1. e4 1-0"

    set_active_player(second["id"])
    other_stats = local_stats()
    assert other_stats["games_played"] == 0
    assert other_stats["puzzle_attempts"] == 0
