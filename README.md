# Chess V2 Web

This folder now contains the first web-app version of Chess V2 while keeping
the original `chess_game.py` Pygame file as a reference.

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
    styles.css     Cosmic CHESS V2 styling
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

## Notes

The Play page already renders the board, timers, move history, captured pieces,
chat/meme panel, and core action buttons. Bot Battle and Puzzle pages are
scaffolded for later, as requested.

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
