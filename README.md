# Chess V2 Web

CHESS V2 is a dark-fantasy chess game and learning platform where chess
concepts are taught as trials, analysis becomes a post-battle autopsy, puzzles
become training encounters, and bots will eventually become characters with
distinct personalities.

This folder contains the web-app version of CHESS V2 while keeping the
original `chess_game.py` Pygame file as a reference.

## Stack

- Frontend: React + Vite
- Backend: FastAPI
- Database: SQLite first, PostgreSQL later
- Realtime: WebSocket
- Deployment target: Vercel for frontend, Render for backend

## Project Layout

```text
backend/
  app/
    main.py        FastAPI routes and WebSocket room
    database.py    SQLite schema and connection helpers
  requirements.txt

frontend/
  src/
    main.jsx       React pages and chess screen
    styles.css     Dark-fantasy CHESS V2 styling
  package.json
  vite.config.js

chess_core/        Adapters between old CHESS V2 boards and python-chess
ai/                GUI-safe bot and puzzle managers
ml/                Machine-learning data, encoders, models, and training code
docs/              Technical architecture notes
tests/             Critical ML infrastructure tests
```

## Local Run

Backend:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

## Vercel Frontend and Render Backend

The repository includes a root `vercel.json` so Vercel can deploy the Vite
frontend from this monorepo. In Vercel, use the repository root as the project
root. The configuration builds `frontend` and publishes `frontend/dist`.

Set these Vercel environment variables for Preview and Production:

```text
VITE_API_TARGET=https://your-chess-v2-backend.onrender.com
VITE_GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
```

For the FastAPI service on Render, use:

```text
Root Directory: backend
Build Command: pip install -r requirements.txt
Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
Health Check Path: /health
```

Set these Render environment variables:

```text
CHESS_V2_SECRET=<long-random-secret>
CORS_ORIGINS=https://your-vercel-project.vercel.app
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
STOCKFISH_PATH=<path to a Linux Stockfish binary, when analysis is enabled>
```

`render.yaml` contains the backend service definition. SQLite is suitable for
local development, but Render's filesystem is not a permanent database, so a
managed PostgreSQL database should be added before production accounts and
history are introduced. Stockfish also needs a Linux executable on Render;
the Windows path in local development will not work there.

## Database Tables

The SQLite database is created automatically at `backend/data/chess_v2.sqlite3`
when the FastAPI app starts. It includes:

- users
- games
- moves
- ratings
- puzzles
- user_puzzle_attempts
- memes
- local_games and local_moves for private local match records
- local_game_reflections for player-authored intentions and post-game notes
- local_chronicles for private Stockfish-backed Match Chronicles

## Notes

The Play page records move FENs, SAN/UCI moves, clock time, captures, and finish
reasons. Completed local games can be given a player intention and reflection,
then opened as a private Match Chronicle from Profile or the finished-game
panel. Chronicles include engine metadata, evaluation timelines, pressure data,
and an interactive Try the Moment board. Imported PGNs remain available for
one-off analysis without being saved to local history.

The current Chronicle loop is intentionally local-first. Online matchmaking,
friend rooms, public sharing, ratings, and permanent account synchronization
remain later stages after the private game lifecycle is dependable.

## ML Foundation

The serious AI system starts separately from the UI. The first foundation files
are:

- `chess_core/adapter.py` for old pygame board arrays to `python-chess`
- `ml/common/board_encoder.py` for deterministic `18 x 8 x 8` board tensors
- `ml/common/move_encoder.py` for the fixed neural action vocabulary
- `ml/data/build_policy_shards.py` for streaming PGN to Parquet policy shards
- `ml/bot/policy_model.py` and `ml/bot/inference.py` for the first rating-conditioned human policy bot

Install the lightweight ML dependencies:

```bash
pip install -r requirements-ml.txt
```

Run the foundation tests:

```bash
python -m pytest tests
```

Read the full architecture note at `docs/ML_ARCHITECTURE.md`.

## Stockfish Bot

Stockfish is configured locally at:

```text
C:\Users\charl\Downloads\stockfish-windows-x86-64-avx2\stockfish\stockfish-windows-x86-64-avx2.exe
```

You can override that path with the `STOCKFISH_PATH` environment variable.
Test the executable directly:

```bash
python test_stockfish.py
```

The web Bot Battle page also includes Stockfish. Start the backend first so the
frontend can call `POST /api/bot/stockfish/move`. The backend keeps one
Stockfish process alive and closes it during shutdown.

Puzzle move sequences can be checked with:

```bash
python puzzle_validation.py
```

## Stabilization Work

The current local foundation also includes:

- `chess_core/game_controller.py`: authoritative `python-chess` board, legal moves, undo, captures, FEN, and PGN
- `puzzles/puzzle_importer.py`: Lichess-style trigger-move normalization and rejection of illegal records
- `puzzles/puzzle_session.py`: UCI-based multi-step puzzle gameplay with forced replies
- local SQLite profile, game, move, and puzzle-attempt endpoints under `/api/local/*`

The bundled puzzle file currently contains four official Lichess sample records.
It is a smoke sample, not the full 100-puzzle production set. Download the
official `lichess_db_puzzle.csv.zst` export into `data/raw`, then import it with:

```bash
python -m puzzles.puzzle_importer --input data/raw/lichess_db_puzzle.csv.zst --output frontend/public/assets/puzzles/puzzles.json --limit 100
```

The official source is the [Lichess open database](https://database.lichess.org/).
