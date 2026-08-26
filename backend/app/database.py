from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "chess_v2.sqlite3"


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    display_name TEXT,
    avatar TEXT,
    bio TEXT,
    favorite_theme TEXT,
    google_sub TEXT UNIQUE,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    white_player_id INTEGER,
    black_player_id INTEGER,
    result TEXT,
    time_control TEXT,
    pgn TEXT,
    fen_final TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at TEXT,
    FOREIGN KEY (white_player_id) REFERENCES users(id),
    FOREIGN KEY (black_player_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS moves (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL,
    move_number INTEGER NOT NULL,
    player_color TEXT NOT NULL CHECK (player_color IN ('white', 'black')),
    move_san TEXT NOT NULL,
    move_uci TEXT NOT NULL,
    fen_after TEXT,
    time_left INTEGER,
    FOREIGN KEY (game_id) REFERENCES games(id)
);

CREATE TABLE IF NOT EXISTS ratings (
    user_id INTEGER NOT NULL,
    mode TEXT NOT NULL,
    rating INTEGER NOT NULL DEFAULT 1200,
    wins INTEGER NOT NULL DEFAULT 0,
    losses INTEGER NOT NULL DEFAULT 0,
    draws INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, mode),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS puzzles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fen TEXT NOT NULL,
    solution TEXT NOT NULL,
    theme TEXT,
    difficulty INTEGER,
    source TEXT
);

CREATE TABLE IF NOT EXISTS user_puzzle_attempts (
    user_id INTEGER NOT NULL,
    puzzle_id INTEGER NOT NULL,
    correct INTEGER NOT NULL CHECK (correct IN (0, 1)),
    time_taken INTEGER,
    attempted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, puzzle_id, attempted_at),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (puzzle_id) REFERENCES puzzles(id)
);

CREATE TABLE IF NOT EXISTS memes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trigger_type TEXT NOT NULL,
    file_path TEXT NOT NULL,
    caption TEXT,
    rarity TEXT NOT NULL DEFAULT 'common'
);

CREATE TABLE IF NOT EXISTS local_profile (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    username TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    display_name TEXT,
    avatar TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_active_at TEXT
);

CREATE TABLE IF NOT EXISTS active_profile (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    player_id INTEGER,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (player_id) REFERENCES players(id)
);

CREATE TABLE IF NOT EXISTS player_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER NOT NULL,
    setting_key TEXT NOT NULL,
    setting_value TEXT NOT NULL,
    UNIQUE(player_id, setting_key),
    FOREIGN KEY (player_id) REFERENCES players(id)
);

CREATE TABLE IF NOT EXISTS local_games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER,
    white_name TEXT NOT NULL,
    black_name TEXT NOT NULL,
    mode TEXT NOT NULL,
    opponent_type TEXT NOT NULL DEFAULT 'human',
    opponent_name TEXT,
    player_color TEXT,
    result TEXT NOT NULL DEFAULT '*',
    result_reason TEXT,
    pgn TEXT,
    starting_fen TEXT,
    final_fen TEXT,
    total_moves INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT,
    ended_at TEXT,
    FOREIGN KEY (player_id) REFERENCES players(id)
);

CREATE TABLE IF NOT EXISTS local_moves (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id INTEGER NOT NULL,
    ply INTEGER NOT NULL,
    uci TEXT NOT NULL,
    san TEXT NOT NULL,
    move_number INTEGER,
    color TEXT,
    fen_before TEXT,
    fen_after TEXT NOT NULL,
    moved_at TEXT,
    time_left INTEGER,
    FOREIGN KEY (game_id) REFERENCES local_games(id)
);

CREATE TABLE IF NOT EXISTS local_puzzle_attempts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER,
    puzzle_id TEXT NOT NULL,
    puzzle_rating INTEGER,
    themes TEXT,
    correct INTEGER NOT NULL CHECK (correct IN (0, 1)),
    attempts INTEGER NOT NULL DEFAULT 1,
    time_taken INTEGER,
    attempted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (player_id) REFERENCES players(id)
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def get_connection():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        conn.executescript(SCHEMA)
        conn.execute("INSERT OR IGNORE INTO local_profile (id, username) VALUES (1, 'Player')")
        _ensure_user_columns(conn)
        _ensure_local_columns(conn)
        conn.commit()


def _ensure_user_columns(conn):
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
    columns = {
        "display_name": "TEXT",
        "bio": "TEXT",
        "favorite_theme": "TEXT",
        "google_sub": "TEXT UNIQUE",
    }
    for name, definition in columns.items():
        if name not in existing:
            try:
                conn.execute(f"ALTER TABLE users ADD COLUMN {name} {definition}")
            except sqlite3.OperationalError:
                if name == "google_sub":
                    conn.execute("ALTER TABLE users ADD COLUMN google_sub TEXT")
                else:
                    raise


def _ensure_local_columns(conn):
    """Migrate the original single-profile tables without losing local data."""
    columns_by_table = {
        "local_games": {
            "player_id": "INTEGER",
            "opponent_type": "TEXT NOT NULL DEFAULT 'human'",
            "opponent_name": "TEXT",
            "player_color": "TEXT",
            "result_reason": "TEXT",
            "starting_fen": "TEXT",
            "total_moves": "INTEGER NOT NULL DEFAULT 0",
            "updated_at": "TEXT",
        },
        "local_moves": {
            "move_number": "INTEGER",
            "color": "TEXT",
            "fen_before": "TEXT",
            "moved_at": "TEXT",
        },
        "local_puzzle_attempts": {
            "player_id": "INTEGER",
            "puzzle_rating": "INTEGER",
            "themes": "TEXT",
            "attempted_at": "TEXT",
        },
    }
    for table, columns in columns_by_table.items():
        existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        for name, definition in columns.items():
            if name not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")

    conn.execute(
        """
        INSERT OR IGNORE INTO players
            (username, display_name, created_at, updated_at, last_active_at)
        SELECT username, username, created_at, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        FROM local_profile WHERE id = 1
        """
    )
    player = conn.execute("SELECT id FROM players ORDER BY id LIMIT 1").fetchone()
    if player:
        conn.execute(
            """
            INSERT OR IGNORE INTO active_profile (id, player_id, updated_at)
            VALUES (1, ?, CURRENT_TIMESTAMP)
            """,
            (player["id"],),
        )
        conn.execute(
            "UPDATE local_games SET player_id = ? WHERE player_id IS NULL",
            (player["id"],),
        )
        conn.execute(
            "UPDATE local_puzzle_attempts SET player_id = ? WHERE player_id IS NULL",
            (player["id"],),
        )

    conn.execute("CREATE INDEX IF NOT EXISTS idx_local_games_player_id ON local_games(player_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_local_moves_game_id ON local_moves(game_id)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_local_puzzle_attempts_player_id ON local_puzzle_attempts(player_id)"
    )


def row_to_dict(row):
    return dict(row) if row is not None else None
