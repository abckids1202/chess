from backend.app.database import init_db
from backend.app.main import (
    HTTPException,
    LocalGameCreate,
    LocalMoveCreate,
    create_local_game,
    delete_last_local_move,
    save_local_move,
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
