from typing import Any, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .database import get_connection, init_db, row_to_dict


app = FastAPI(title="Chess V2 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.get("/health")
def health():
    return {"ok": True, "service": "chess-v2-api"}


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
