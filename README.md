# Chess V2 Web

This folder now contains the first web-app version of Chess V2 while keeping
the original `chess_v2.py` Pygame file as a reference.

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
