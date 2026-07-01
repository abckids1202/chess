import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { Chess } from "chess.js";
import "./styles.css";

const tabs = ["Home", "Play", "Bot Battle", "Puzzle", "Analysis", "Profile", "Leaderboard"];

const pieceLabels = {
  p: "P",
  n: "N",
  b: "B",
  r: "R",
  q: "Q",
  k: "K"
};

function App() {
  const [page, setPage] = useState("Home");

  return (
    <main className="app-shell">
      <Starfield />
      <nav className="top-nav">
        <button className="brand" onClick={() => setPage("Home")}>CHESS V2</button>
        <div className="nav-tabs">
          {tabs.map((tab) => (
            <button
              key={tab}
              className={page === tab ? "active" : ""}
              onClick={() => setPage(tab)}
            >
              {tab}
            </button>
          ))}
        </div>
        <button className="login-button">Login</button>
      </nav>

      {page === "Home" && <HomePage onPlay={() => setPage("Play")} />}
      {page === "Play" && <PlayPage />}
      {page === "Bot Battle" && <BotBattlePage />}
      {page === "Puzzle" && <PuzzlePage />}
      {page === "Analysis" && <AnalysisPage />}
      {page === "Profile" && <ProfilePage />}
      {page === "Leaderboard" && <LeaderboardPage />}
    </main>
  );
}

function Starfield() {
  return (
    <div className="starfield" aria-hidden="true">
      {Array.from({ length: 90 }).map((_, index) => (
        <span
          key={index}
          style={{
            left: `${(index * 37) % 100}%`,
            top: `${(index * 53) % 100}%`,
            animationDelay: `${(index % 12) * 0.3}s`
          }}
        />
      ))}
    </div>
  );
}

function HomePage({ onPlay }) {
  return (
    <section className="page home-layout">
      <div className="hero-copy">
        <p className="eyebrow">cosmic chess, now on the web</p>
        <h1>CHESS V2</h1>
        <p>
          yo
        </p>
        <div className="hero-actions">
          <button className="primary-action" onClick={onPlay}>Play</button>
          <button className="secondary-action">Login</button>
        </div>
      </div>
      <ThemePreview />
      <div className="feature-grid">
        {["Realtime play", "Meme mode", "Chess clocks", "PGN analysis"].map((item) => (
          <article className="feature-card" key={item}>
            <h3>{item}</h3>
            <p>yo</p>
          </article>
        ))}
      </div>
    </section>
  );
}

function ThemePreview() {
  return (
    <div className="theme-preview">
      <div className="mini-board">
        {Array.from({ length: 64 }).map((_, i) => (
          <div className={(Math.floor(i / 8) + i) % 2 === 0 ? "light" : "dark"} key={i} />
        ))}
      </div>
      <div className="preview-panel">
        <strong>Theme preview</strong>
      </div>
    </div>
  );
}

function PlayPage() {
  const gameRef = useRef(new Chess());
  const [board, setBoard] = useState(gameRef.current.board());
  const [selected, setSelected] = useState(null);
  const [moves, setMoves] = useState([]);
  const [captured, setCaptured] = useState({ w: [], b: [] });
  const [premove, setPremove] = useState(null);
  const [socketStatus, setSocketStatus] = useState("offline");
  const [chat, setChat] = useState([
    { from: "system", text: "Welcome to CHESS V2." },
    { from: "meme", text: "Capture memes will live here." }
  ]);

  useEffect(() => {
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${protocol}://${window.location.host}/ws/game/demo-game`);
    ws.onopen = () => setSocketStatus("online");
    ws.onclose = () => setSocketStatus("offline");
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "chat" || data.type === "system") {
          setChat((items) => [...items.slice(-5), { from: data.type, text: data.message }]);
        }
      } catch {
        setChat((items) => [...items.slice(-5), { from: "system", text: event.data }]);
      }
    };
    return () => ws.close();
  }, []);

  const turn = gameRef.current.turn() === "w" ? "WHITE" : "BLACK";
  const moveHistory = gameRef.current.history();

  function squareName(row, col) {
    return "abcdefgh"[col] + (8 - row);
  }

  function handleSquare(row, col) {
    const square = squareName(row, col);
    const piece = gameRef.current.get(square);

    if (!selected) {
      if (piece && piece.color === gameRef.current.turn()) {
        setSelected(square);
      } else if (piece) {
        setPremove({ from: square, to: square });
      }
      return;
    }

    const before = gameRef.current.get(square);
    const move = gameRef.current.move({ from: selected, to: square, promotion: "q" });
    if (!move) {
      if (piece && piece.color === gameRef.current.turn()) {
        setSelected(square);
      } else {
        setPremove({ from: selected, to: square });
        setSelected(null);
      }
      return;
    }

    if (before || move.captured) {
      setCaptured((state) => ({
        ...state,
        [move.color === "w" ? "b" : "w"]: [
          ...state[move.color === "w" ? "b" : "w"],
          move.captured || before.type
        ]
      }));
    }
    setSelected(null);
    setPremove(null);
    setBoard(gameRef.current.board());
    setMoves(gameRef.current.history({ verbose: true }));
  }

  function resetGame() {
    gameRef.current = new Chess();
    setBoard(gameRef.current.board());
    setSelected(null);
    setPremove(null);
    setCaptured({ w: [], b: [] });
    setMoves([]);
  }

  function undoMove() {
    gameRef.current.undo();
    setBoard(gameRef.current.board());
    setMoves(gameRef.current.history({ verbose: true }));
  }

  return (
    <section className="page play-layout">
      <div className="board-zone">
        <div className="turn-line">{turn} TO MOVE</div>
        <ChessBoard
          board={board}
          selected={selected}
          premove={premove}
          onSquare={handleSquare}
        />
      </div>
      <aside className="game-panel">
        <h2>CHESS V2</h2>
        <div className="socket-pill">Realtime: {socketStatus}</div>
        <TimerBlock label="BLACK" time="10:00" active={turn === "BLACK"} />
        <TimerBlock label="WHITE" time="10:00" active={turn === "WHITE"} />
        <CapturedPieces captured={captured} />
        <MoveHistory moves={moveHistory} />
        <div className="action-row">
          <button>Resign</button>
          <button>Draw</button>
          <button onClick={undoMove}>Undo</button>
          <button onClick={resetGame}>Reset</button>
        </div>
        <ChatPanel chat={chat} />
      </aside>
    </section>
  );
}

function ChessBoard({ board, selected, premove, onSquare }) {
  return (
    <div className="chess-board">
      {board.flatMap((row, rowIndex) =>
        row.map((piece, colIndex) => {
          const square = "abcdefgh"[colIndex] + (8 - rowIndex);
          const isLight = (rowIndex + colIndex) % 2 === 0;
          const isSelected = selected === square;
          const isPremove = premove && (premove.from === square || premove.to === square);
          return (
            <button
              className={[
                "square",
                isLight ? "light" : "dark",
                isSelected ? "selected" : "",
                isPremove ? "premove" : ""
              ].join(" ")}
              key={square}
              onClick={() => onSquare(rowIndex, colIndex)}
            >
              {piece && (
                <span className={`piece ${piece.color}`}>
                  {piece.color.toUpperCase()}{pieceLabels[piece.type]}
                </span>
              )}
            </button>
          );
        })
      )}
    </div>
  );
}

function TimerBlock({ label, time, active }) {
  return (
    <div className={`timer-block ${active ? "active" : ""}`}>
      <span>{label}</span>
      <strong>{time}</strong>
    </div>
  );
}

function CapturedPieces({ captured }) {
  return (
    <section className="panel-section">
      <h3>Captured pieces</h3>
      <p>White captured: {captured.b.join(" ") || "none"}</p>
      <p>Black captured: {captured.w.join(" ") || "none"}</p>
    </section>
  );
}

function MoveHistory({ moves }) {
  const rows = [];
  for (let i = 0; i < moves.length; i += 2) {
    rows.push(`${i / 2 + 1}. ${moves[i] || ""} ${moves[i + 1] || ""}`);
  }
  return (
    <section className="move-log">
      <h3>Move history</h3>
      {rows.length ? rows.map((row) => <p key={row}>{row}</p>) : <p>No moves yet.</p>}
    </section>
  );
}

function ChatPanel({ chat }) {
  return (
    <section className="chat-panel">
      <h3>Chat / Meme panel</h3>
      {chat.map((item, index) => (
        <p key={`${item.from}-${index}`}><strong>{item.from}:</strong> {item.text}</p>
      ))}
      <div className="chat-input">
        <input placeholder="Message" />
        <button>Send</button>
      </div>
    </section>
  );
}

function BotBattlePage() {
  return (
    <PlaceholderPage
      title="Bot Battle"
      items={["Choose bot level", "Choose bot personality", "Start game"]}
    />
  );
}

function PuzzlePage() {
  return (
    <PlaceholderPage
      title="Puzzle"
      items={["Daily puzzle", "Puzzle categories", "Streak system"]}
    />
  );
}

function AnalysisPage() {
  return (
    <PlaceholderPage
      title="Analysis"
      items={["Upload PGN", "Analyze game", "Show mistakes and blunders"]}
    />
  );
}

function ProfilePage() {
  return (
    <PlaceholderPage
      title="Profile"
      items={["Username", "Rating", "Game history", "Puzzle stats", "Favorite memes/theme"]}
    />
  );
}

function LeaderboardPage() {
  return (
    <PlaceholderPage
      title="Leaderboard"
      items={["Rapid rating", "Blitz rating", "Bullet rating", "Puzzle rating", "Meme mode ranking"]}
    />
  );
}

function PlaceholderPage({ title, items }) {
  return (
    <section className="page placeholder-layout">
      <h1>{title}</h1>
      <div className="placeholder-grid">
        {items.map((item) => (
          <article className="feature-card" key={item}>
            <h3>{item}</h3>
            <p>idk</p>
          </article>
        ))}
      </div>
    </section>
  );
}

createRoot(document.getElementById("root")).render(<App />);
