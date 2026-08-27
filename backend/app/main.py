import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from datetime import datetime
from typing import Any, Optional

import chess
import chess.engine
from fastapi import FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .analysis.analysis_service import analyze_pgn
from .analysis.engine_score import is_forced_mate
from .analysis.move_classifier import classify_move, evaluation_loss, move_commentary
from .analysis.stockfish_analyzer import StockfishAnalyzer
from .database import get_connection, init_db, row_to_dict
from .local_storage import (
    create_player,
    get_local_chronicle,
    get_local_game_record,
    get_game_history,
    get_active_player,
    get_all_players,
    get_local_leaderboard,
    get_all_settings,
    get_player_stats,
    save_game_reflection,
    save_local_chronicle,
    set_setting,
    set_active_player,
    update_player,
)
from .puzzle_validation import validate_puzzle
from .stockfish_bot import StockfishBot


app = FastAPI(title="Chess V2 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TOKEN_SECRET = os.getenv("CHESS_V2_SECRET", "dev-only-change-me")
TOKEN_TTL_SECONDS = 60 * 60 * 24 * 14
STOCKFISH_PATH = os.getenv(
    "STOCKFISH_PATH",
    r"C:\Users\charl\Downloads\stockfish-windows-x86-64-avx2\stockfish\stockfish-windows-x86-64-avx2.exe",
)
stockfish_instance: Optional[StockfishBot] = None


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64url(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _hash_password(password: str, salt: Optional[str] = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120000)
    return f"{salt}${digest.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    if not stored or "$" not in stored:
        return False
    salt, expected = stored.split("$", 1)
    return hmac.compare_digest(_hash_password(password, salt), stored)


def _make_token(user_id: int) -> str:
    payload = {"sub": user_id, "exp": int(time.time()) + TOKEN_TTL_SECONDS}
    body = _b64url(json.dumps(payload, separators=(",", ":")).encode())
    sig = hmac.new(TOKEN_SECRET.encode(), body.encode(), hashlib.sha256).digest()
    return f"{body}.{_b64url(sig)}"


def _read_token(token: str) -> int:
    try:
        body, sig = token.split(".", 1)
        expected = _b64url(hmac.new(TOKEN_SECRET.encode(), body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected):
            raise ValueError("bad signature")
        payload = json.loads(_unb64url(body))
        if payload["exp"] < time.time():
            raise ValueError("expired")
        return int(payload["sub"])
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc


def _user_public(row):
    user = row_to_dict(row)
    if not user:
        return None
    user.pop("password_hash", None)
    user.pop("avatar", None)
    user.pop("bio", None)
    return user


def _auth_user(authorization: Optional[str]) -> int:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    return _read_token(authorization.split(" ", 1)[1])


class GameCreate(BaseModel):
    white_player_id: Optional[int] = None
    black_player_id: Optional[int] = None
    time_control: str = "10+0"


class MoveCreate(BaseModel):
    game_id: int
    move_number: int
    player_color: str
    move_san: str
    move_uci: str
    fen_after: Optional[str] = None
    time_left: Optional[int] = None


class RegisterCreate(BaseModel):
    username: str
    email: str
    password: str
    display_name: Optional[str] = None
    favorite_theme: Optional[str] = None


class LoginCreate(BaseModel):
    login: str
    password: str


class GoogleLoginCreate(BaseModel):
    credential: str
    username: Optional[str] = None


class ProfileUpdate(BaseModel):
    username: Optional[str] = None
    display_name: Optional[str] = None
    favorite_theme: Optional[str] = None


class StockfishMoveCreate(BaseModel):
    fen: str
    skill_level: int = 5
    move_time: float = 0.5


class AnalysisCreate(BaseModel):
    game_id: Optional[int] = None
    pgn: Optional[str] = None
    skill_level: int = 5
    analysis_time: float = 0.25
    max_plies: int = 120


class TryMomentCreate(BaseModel):
    fen: str
    move_uci: str
    skill_level: int = 5
    analysis_time: float = 0.25


class PuzzleValidationCreate(BaseModel):
    fen: str
    moves_uci: list[str]


class LocalProfileUpdate(BaseModel):
    username: str


class LocalPlayerCreate(BaseModel):
    username: str


class LocalSettingUpdate(BaseModel):
    key: str
    value: Any


class LocalGameCreate(BaseModel):
    white_name: str = "Player"
    black_name: str = "Player"
    mode: str = "local"
    time_control: str = "10+0"
    intention: Optional[str] = None


class LocalMoveCreate(BaseModel):
    ply: int
    uci: str
    san: str
    fen_after: str
    time_left: Optional[int] = None


class LocalGameFinish(BaseModel):
    result: str
    result_reason: str = "manual"
    pgn: Optional[str] = None
    final_fen: Optional[str] = None


class LocalGameUpdate(BaseModel):
    intention: Optional[str] = None


class LocalReflectionCreate(BaseModel):
    intention: Optional[str] = None
    feeling: Optional[str] = None
    note: Optional[str] = None


class LocalPuzzleAttemptCreate(BaseModel):
    puzzle_id: str
    correct: bool
    attempts: int = 1
    time_taken: Optional[int] = None
    puzzle_rating: Optional[int] = None
    themes: list[str] = []


class ConnectionManager:
    def __init__(self):
        self.rooms: dict[str, set[WebSocket]] = {}

    async def connect(self, game_id: str, websocket: WebSocket):
        await websocket.accept()
        self.rooms.setdefault(game_id, set()).add(websocket)

    def disconnect(self, game_id: str, websocket: WebSocket):
        sockets = self.rooms.get(game_id)
        if not sockets:
            return
        sockets.discard(websocket)
        if not sockets:
            self.rooms.pop(game_id, None)

    async def broadcast(self, game_id: str, message: dict[str, Any]):
        for socket in list(self.rooms.get(game_id, set())):
            await socket.send_json(message)


manager = ConnectionManager()


@app.on_event("startup")
def on_startup():
    init_db()


@app.on_event("shutdown")
def on_shutdown():
    global stockfish_instance
    if stockfish_instance is not None:
        stockfish_instance.close()
        stockfish_instance = None


def get_stockfish(skill_level: int = 5) -> StockfishBot:
    global stockfish_instance
    if stockfish_instance is None:
        try:
            stockfish_instance = StockfishBot(STOCKFISH_PATH, skill_level=skill_level)
        except (FileNotFoundError, OSError) as exc:
            raise HTTPException(
                status_code=503,
                detail=f"Stockfish is unavailable. Set STOCKFISH_PATH. {exc}",
            ) from exc
    elif stockfish_instance.skill_level != skill_level:
        stockfish_instance.set_skill_level(skill_level)
    return stockfish_instance


@app.get("/health")
def health():
    return {"ok": True, "service": "chess-v2-api"}


@app.post("/api/bot/stockfish/move")
def stockfish_move(payload: StockfishMoveCreate):
    try:
        board = chess.Board(payload.fen)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid FEN: {exc}") from exc

    if not 0 <= payload.skill_level <= 20:
        raise HTTPException(status_code=400, detail="skill_level must be between 0 and 20")
    if not 0.01 <= payload.move_time <= 30:
        raise HTTPException(status_code=400, detail="move_time must be between 0.01 and 30 seconds")

    bot = get_stockfish(payload.skill_level)
    started = time.perf_counter()
    try:
        move = bot.choose_move(board, move_time=payload.move_time)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {
        "move": move.uci(),
        "san": board.san(move),
        "fen_after": _fen_after(board, move),
        "thinking_time_ms": round((time.perf_counter() - started) * 1000),
    }


@app.post("/api/analysis")
def analyze_game(payload: AnalysisCreate):
    if not 0 <= payload.skill_level <= 20:
        raise HTTPException(status_code=400, detail="skill_level must be between 0 and 20")
    if not 0.05 <= payload.analysis_time <= 5:
        raise HTTPException(status_code=400, detail="analysis_time must be between 0.05 and 5 seconds")
    if not 1 <= payload.max_plies <= 240:
        raise HTTPException(status_code=400, detail="max_plies must be between 1 and 240")

    active_player = get_active_player()
    game_record = None
    source = "pgn"
    if payload.game_id is not None:
        game_record = get_local_game_record(active_player["id"], payload.game_id)
        if not game_record:
            raise HTTPException(status_code=404, detail="Saved local game not found")
        pgn_text = (game_record.get("pgn") or "").strip()
        source = "saved_game"
    else:
        pgn_text = (payload.pgn or "").strip()
    if not pgn_text:
        raise HTTPException(status_code=400, detail="Please choose a saved game or paste a PGN before analyzing.")

    try:
        engine = get_stockfish(payload.skill_level)
        analyzer = StockfishAnalyzer(
            analysis_time=payload.analysis_time,
            engine=engine,
        )
        report = analyze_pgn(pgn_text, analyzer, max_plies=payload.max_plies)
        report["engine"] = {
            "name": "Stockfish",
            "skill_level": payload.skill_level,
            "analysis_time": payload.analysis_time,
        }
        report["game_info"]["source"] = source
        if game_record:
            report["game_info"]["game_id"] = game_record["id"]
            time_by_ply = {
                move["ply"]: move.get("time_left")
                for move in game_record.get("moves", [])
            }
            for move in report["moves"]:
                move["time_left"] = time_by_ply.get(move["ply"])
            for point in report["evaluation_timeline"]:
                point["time_left"] = time_by_ply.get(point["ply"])
            report["reflection"] = {
                "intention": game_record.get("reflection_intention") or game_record.get("intention"),
                "feeling": game_record.get("reflection_feeling"),
                "note": game_record.get("reflection_note"),
            }
        else:
            report["reflection"] = {"intention": None, "feeling": None, "note": None}

        report["pressure_moments"] = [
            move for move in report["moves"]
            if move.get("time_left") is not None and move["time_left"] <= 30
        ][:5]
        report["chronicle_saved"] = bool(game_record)
        if game_record:
            save_local_chronicle(
                active_player["id"],
                game_record["id"],
                report,
                engine_name="Stockfish",
                engine_skill=payload.skill_level,
                analysis_time=payload.analysis_time,
            )
        return report
    except HTTPException:
        raise
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=f"Stockfish path is unavailable. {exc}") from exc
    except chess.engine.EngineError as exc:
        raise HTTPException(status_code=503, detail="Stockfish stopped while analyzing this game.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/api/analysis/try-moment")
def try_analysis_moment(payload: TryMomentCreate):
    if not 0 <= payload.skill_level <= 20:
        raise HTTPException(status_code=400, detail="skill_level must be between 0 and 20")
    if not 0.05 <= payload.analysis_time <= 5:
        raise HTTPException(status_code=400, detail="analysis_time must be between 0.05 and 5 seconds")
    try:
        board = chess.Board(payload.fen)
        played_move = chess.Move.from_uci(payload.move_uci)
        if played_move not in board.legal_moves:
            raise ValueError("The selected move is not legal in this position.")
        played_san = board.san(played_move)
        engine = get_stockfish(payload.skill_level)
        analyzer = StockfishAnalyzer(analysis_time=payload.analysis_time, engine=engine)
        before_result = analyzer.analyze_position(board)
        best_move = before_result["best_move"]
        if best_move is None:
            raise RuntimeError("Stockfish returned no best move for this position.")

        best_san = board.san(best_move)
        best_board = board.copy(stack=False)
        best_board.push(best_move)
        best_after = analyzer.analyze_position(best_board)
        played_board = board.copy(stack=False)
        played_board.push(played_move)
        played_after = analyzer.analyze_position(played_board)
        before_score = before_result["score"]
        best_after_score = best_after["score"]
        after_score = played_after["score"]
        color = "white" if board.turn == chess.WHITE else "black"
        loss = evaluation_loss(color, best_after_score["numeric"], after_score["numeric"])
        classification = classify_move(
            loss,
            best_is_mate=is_forced_mate(best_after_score),
            played_is_opponent_mate=is_forced_mate(after_score) and (
                (color == "white" and after_score["numeric"] <= -100.0)
                or (color == "black" and after_score["numeric"] >= 100.0)
            ),
            is_best_move=played_move == best_move,
        )
        return {
            "played_move_uci": played_move.uci(),
            "played_move_san": played_san,
            "best_move_uci": best_move.uci(),
            "best_move_san": best_san,
            "eval_before": before_score["numeric"],
            "eval_after": after_score["numeric"],
            "eval_before_display": before_score["display"],
            "eval_after_display": after_score["display"],
            "best_after_score": best_after_score,
            "eval_loss": loss,
            "classification": classification,
            "commentary": move_commentary(classification, loss, best_san),
            "fen_after": played_board.fen(),
            "engine": {
                "name": "Stockfish",
                "skill_level": payload.skill_level,
                "analysis_time": payload.analysis_time,
            },
        }
    except HTTPException:
        raise
    except chess.engine.EngineError as exc:
        raise HTTPException(status_code=503, detail="Stockfish stopped while comparing this moment.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


def _fen_after(board: chess.Board, move: chess.Move) -> str:
    next_board = board.copy(stack=False)
    next_board.push(move)
    return next_board.fen()


@app.post("/api/puzzles/validate")
def validate_puzzle_route(payload: PuzzleValidationCreate):
    valid, message = validate_puzzle(payload.fen, payload.moves_uci)
    return {"valid": valid, "message": message}


@app.get("/api/local/profile")
def get_local_profile():
    return get_active_player()


@app.put("/api/local/profile")
def update_local_profile(payload: LocalProfileUpdate):
    try:
        return update_player(get_active_player()["id"], payload.username)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/local/players")
def list_local_players():
    active = get_active_player()
    return {"active_player_id": active["id"], "players": get_all_players()}


@app.post("/api/local/players")
def create_local_player(payload: LocalPlayerCreate):
    try:
        return set_active_player(create_player(payload.username)["id"])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/local/players/{player_id}/activate")
def activate_local_player(player_id: int):
    try:
        return set_active_player(player_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/local/settings")
def get_local_settings():
    return get_all_settings(get_active_player()["id"])


@app.put("/api/local/settings")
def update_local_setting(payload: LocalSettingUpdate):
    try:
        set_setting(get_active_player()["id"], payload.key, payload.value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return get_all_settings(get_active_player()["id"])


@app.post("/api/local/games")
def create_local_game(payload: LocalGameCreate):
    active = get_active_player()
    white_name = payload.white_name.strip() or "Player"
    black_name = payload.black_name.strip() or "Opponent"
    time_control = payload.time_control.strip()[:24] or "10+0"
    intention = (payload.intention or "").strip()[:80] or None
    if white_name == active["username"]:
        player_color = "white"
        opponent_name = black_name
    elif black_name == active["username"]:
        player_color = "black"
        opponent_name = white_name
    else:
        player_color = "unknown"
        opponent_name = black_name
    opponent_type = "local_player" if payload.mode in {"local", "local_1v1"} else "bot"
    if "stockfish" in opponent_name.lower():
        opponent_type = "stockfish"
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO local_games
                (player_id, white_name, black_name, mode, opponent_type,
                 opponent_name, player_color, time_control, intention,
                 starting_fen, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                active["id"], white_name, black_name,
                "local_1v1" if payload.mode == "local" else payload.mode,
                opponent_type, opponent_name, player_color, time_control, intention,
                chess.Board().fen(),
                datetime.now().astimezone().isoformat(timespec="seconds"),
            ),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM local_games WHERE id = ?", (cur.lastrowid,)).fetchone()
    return row_to_dict(row)


@app.get("/api/local/games/history")
def local_game_history(limit: int = 50):
    if not 1 <= limit <= 100:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 100")
    return {"games": get_game_history(get_active_player()["id"], limit)}


@app.get("/api/local/games/{game_id}/chronicle")
def local_game_chronicle(game_id: int):
    chronicle = get_local_chronicle(get_active_player()["id"], game_id)
    if chronicle is None:
        raise HTTPException(status_code=404, detail="Chronicle not found")
    return chronicle


@app.patch("/api/local/games/{game_id}")
def update_local_game(game_id: int, payload: LocalGameUpdate):
    intention = (payload.intention or "").strip()[:80] or None
    with get_connection() as conn:
        cur = conn.execute(
            """
            UPDATE local_games
            SET intention = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND player_id = ?
            """,
            (intention, game_id, get_active_player()["id"]),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Local game not found")
        conn.commit()
        row = conn.execute("SELECT * FROM local_games WHERE id = ?", (game_id,)).fetchone()
    return row_to_dict(row)


@app.post("/api/local/games/{game_id}/reflection")
def create_local_game_reflection(game_id: int, payload: LocalReflectionCreate):
    reflection = save_game_reflection(
        get_active_player()["id"],
        game_id,
        intention=payload.intention,
        feeling=payload.feeling,
        note=payload.note,
    )
    if reflection is None:
        raise HTTPException(status_code=404, detail="Local game not found")
    return reflection


@app.post("/api/local/games/{game_id}/moves")
def save_local_move(game_id: int, payload: LocalMoveCreate):
    with get_connection() as conn:
        game = conn.execute("SELECT id FROM local_games WHERE id = ?", (game_id,)).fetchone()
        if game is None:
            raise HTTPException(status_code=404, detail="Local game not found")
        game = conn.execute("SELECT * FROM local_games WHERE id = ?", (game_id,)).fetchone()
        board = chess.Board(game["starting_fen"] or chess.STARTING_FEN)
        previous_moves = conn.execute(
            "SELECT uci FROM local_moves WHERE game_id = ? ORDER BY ply, id",
            (game_id,),
        ).fetchall()
        try:
            for previous in previous_moves:
                board.push_uci(previous["uci"])
            move = chess.Move.from_uci(payload.uci)
            if move not in board.legal_moves:
                raise ValueError("illegal move")
            fen_before = board.fen()
            color = "white" if board.turn == chess.WHITE else "black"
            expected_san = board.san(move)
            board.push(move)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Move rejected by python-chess: {exc}") from exc
        if expected_san != payload.san:
            raise HTTPException(status_code=400, detail="SAN does not match the validated move")
        stored_ply = len(previous_moves) + 1
        cur = conn.execute(
            """
            INSERT INTO local_moves
                (game_id, ply, uci, san, move_number, color, fen_before,
                 fen_after, moved_at, time_left)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                game_id, stored_ply, payload.uci, expected_san,
                (stored_ply + 1) // 2, color, fen_before, board.fen(),
                datetime.now().astimezone().isoformat(timespec="seconds"),
                payload.time_left,
            ),
        )
        conn.execute(
            "UPDATE local_games SET total_moves = ?, updated_at = ? WHERE id = ?",
            (stored_ply, datetime.now().astimezone().isoformat(timespec="seconds"), game_id),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM local_moves WHERE id = ?", (cur.lastrowid,)).fetchone()
    return row_to_dict(row)


@app.delete("/api/local/games/{game_id}/moves/last")
def delete_last_local_move(game_id: int):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM local_moves WHERE game_id = ? ORDER BY ply DESC, id DESC LIMIT 1",
            (game_id,),
        ).fetchone()
        if row is None:
            return {"deleted": False}
        conn.execute("DELETE FROM local_moves WHERE id = ?", (row["id"],))
        count = conn.execute("SELECT COUNT(*) AS count FROM local_moves WHERE game_id = ?", (game_id,)).fetchone()["count"]
        conn.execute(
            "UPDATE local_games SET result = '*', result_reason = NULL, total_moves = ?, ended_at = NULL WHERE id = ?",
            (count, game_id),
        )
        conn.commit()
    return {"deleted": True}


@app.post("/api/local/games/{game_id}/finish")
def finish_local_game(game_id: int, payload: LocalGameFinish):
    if payload.result not in {"1-0", "0-1", "1/2-1/2", "*"}:
        raise HTTPException(status_code=400, detail="Invalid game result")
    pgn = (payload.pgn or "").strip()
    if payload.result != "*" and not pgn.endswith(payload.result):
        pgn = f"{pgn} {payload.result}".strip()
    with get_connection() as conn:
        cur = conn.execute(
            """
            UPDATE local_games
            SET result = ?, result_reason = ?, pgn = ?, final_fen = ?,
                total_moves = (SELECT COUNT(*) FROM local_moves WHERE game_id = ?),
                updated_at = CURRENT_TIMESTAMP, ended_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (payload.result, payload.result_reason, pgn or None, payload.final_fen, game_id, game_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Local game not found")
        conn.commit()
        row = conn.execute("SELECT * FROM local_games WHERE id = ?", (game_id,)).fetchone()
    return row_to_dict(row)


@app.post("/api/local/puzzle-attempts")
def save_local_puzzle_attempt(payload: LocalPuzzleAttemptCreate):
    player = get_active_player()
    themes = json.dumps(payload.themes or [])
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO local_puzzle_attempts
                (player_id, puzzle_id, puzzle_rating, themes, correct, attempts,
                 time_taken, attempted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                player["id"], payload.puzzle_id, payload.puzzle_rating, themes,
                int(payload.correct), max(1, payload.attempts), payload.time_taken,
                datetime.now().astimezone().isoformat(timespec="seconds"),
            ),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM local_puzzle_attempts WHERE id = ?", (cur.lastrowid,)).fetchone()
    return row_to_dict(row)


def _local_stats():
    profile = get_active_player()
    return {"profile": profile, **get_player_stats(profile["id"])}


@app.get("/api/local/stats")
def local_stats():
    return _local_stats()


@app.get("/api/local/leaderboard")
def local_leaderboard():
    return get_local_leaderboard()


@app.post("/api/auth/register")
def register(payload: RegisterCreate):
    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    with get_connection() as conn:
        try:
            cur = conn.execute(
                """
                INSERT INTO users
                    (username, email, password_hash, display_name, favorite_theme)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    payload.username.strip(),
                    payload.email.strip().lower(),
                    _hash_password(payload.password),
                    payload.display_name,
                    payload.favorite_theme,
                ),
            )
            user_id = cur.lastrowid
            for mode in ("rapid", "blitz", "bullet", "puzzle", "meme"):
                conn.execute("INSERT INTO ratings (user_id, mode) VALUES (?, ?)", (user_id, mode))
            conn.commit()
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Username or email already exists") from exc
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return {"token": _make_token(user_id), "user": _user_public(row)}


@app.post("/api/auth/login")
def login(payload: LoginCreate):
    login_value = payload.login.strip().lower()
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE lower(username) = ? OR lower(email) = ?",
            (login_value, login_value),
        ).fetchone()
    if not row or not _verify_password(payload.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid username/email or password")
    return {"token": _make_token(row["id"]), "user": _user_public(row)}


@app.post("/api/auth/google")
def google_login(payload: GoogleLoginCreate):
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    if not client_id:
        raise HTTPException(status_code=400, detail="GOOGLE_CLIENT_ID is not configured")
    try:
        from google.auth.transport import requests
        from google.oauth2 import id_token

        info = id_token.verify_oauth2_token(
            payload.credential,
            requests.Request(),
            client_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid Google credential") from exc

    google_sub = info["sub"]
    email = info.get("email", "").lower()
    display_name = info.get("name") or payload.username or email.split("@")[0]
    username = payload.username or email.split("@")[0]

    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE google_sub = ?", (google_sub,)).fetchone()
        if row is None:
            base_username = username
            suffix = 1
            while conn.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone():
                suffix += 1
                username = f"{base_username}{suffix}"
            cur = conn.execute(
                """
                INSERT INTO users
                    (username, email, password_hash, display_name, google_sub)
                VALUES (?, ?, ?, ?, ?)
                """,
                (username, email, "google", display_name, google_sub),
            )
            user_id = cur.lastrowid
            for mode in ("rapid", "blitz", "bullet", "puzzle", "meme"):
                conn.execute("INSERT INTO ratings (user_id, mode) VALUES (?, ?)", (user_id, mode))
            conn.commit()
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return {"token": _make_token(row["id"]), "user": _user_public(row)}


@app.get("/api/auth/me")
def me(authorization: Optional[str] = Header(default=None)):
    user_id = _auth_user(authorization)
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user": _user_public(row)}


@app.patch("/api/auth/profile")
def update_profile(payload: ProfileUpdate, authorization: Optional[str] = Header(default=None)):
    user_id = _auth_user(authorization)
    fields = payload.dict(exclude_unset=True)
    allowed = ["username", "display_name", "favorite_theme"]
    updates = [(key, fields[key]) for key in allowed if key in fields]
    if not updates:
        raise HTTPException(status_code=400, detail="No profile fields to update")

    assignments = ", ".join(f"{key} = ?" for key, _ in updates)
    values = [value for _, value in updates]
    values.append(user_id)
    with get_connection() as conn:
        try:
            conn.execute(f"UPDATE users SET {assignments} WHERE id = ?", values)
            conn.commit()
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Username already exists") from exc
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return {"user": _user_public(row)}


@app.post("/api/games")
def create_game(payload: GameCreate):
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO games (white_player_id, black_player_id, time_control)
            VALUES (?, ?, ?)
            """,
            (payload.white_player_id, payload.black_player_id, payload.time_control),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM games WHERE id = ?", (cur.lastrowid,)).fetchone()
    return row_to_dict(row)


@app.get("/api/games/{game_id}")
def get_game(game_id: int):
    with get_connection() as conn:
        game = conn.execute("SELECT * FROM games WHERE id = ?", (game_id,)).fetchone()
        moves = conn.execute(
            "SELECT * FROM moves WHERE game_id = ? ORDER BY move_number, id",
            (game_id,),
        ).fetchall()
    return {"game": row_to_dict(game), "moves": [row_to_dict(row) for row in moves]}


@app.post("/api/moves")
def add_move(payload: MoveCreate):
    with get_connection() as conn:
        cur = conn.execute(
            """
            INSERT INTO moves
                (game_id, move_number, player_color, move_san, move_uci, fen_after, time_left)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.game_id,
                payload.move_number,
                payload.player_color,
                payload.move_san,
                payload.move_uci,
                payload.fen_after,
                payload.time_left,
            ),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM moves WHERE id = ?", (cur.lastrowid,)).fetchone()
    return row_to_dict(row)


@app.get("/api/leaderboard")
def leaderboard(mode: str = "rapid"):
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT users.username, ratings.mode, ratings.rating, ratings.wins,
                   ratings.losses, ratings.draws
            FROM ratings
            JOIN users ON users.id = ratings.user_id
            WHERE ratings.mode = ?
            ORDER BY ratings.rating DESC
            LIMIT 50
            """,
            (mode,),
        ).fetchall()
    return [row_to_dict(row) for row in rows]


@app.websocket("/ws/game/{game_id}")
async def game_socket(websocket: WebSocket, game_id: str):
    await manager.connect(game_id, websocket)
    await manager.broadcast(game_id, {"type": "system", "message": "player connected"})
    try:
        while True:
            data = await websocket.receive_json()
            await manager.broadcast(game_id, data)
    except WebSocketDisconnect:
        manager.disconnect(game_id, websocket)
        await manager.broadcast(game_id, {"type": "system", "message": "player disconnected"})
