import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { Chess } from "chess.js";
import { BOT_DEFINITIONS, BOT_LEVELS, BOT_PERSONALITIES, STOCKFISH_LEVELS } from "./bots";
import { get_legal_moves, make_move } from "./chessEngine";
import { PuzzleManager, loadPuzzles } from "./puzzleManager";
import "./styles.css";

const tabs = ["Home", "Play", "Bot Battle", "Puzzle", "Analysis", "Profile", "Leaderboard"];
const API_TARGET = import.meta.env.VITE_API_TARGET || "";

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || "";
const pieceCodes = { p: "P", n: "N", b: "B", r: "R", q: "Q", k: "K" };
const INITIAL_CLOCK = 10 * 60;
const SOUND_FILES = {
  move: "/assets/sounds/move.mp3",
  capture: "/assets/sounds/capture.mp3",
  castle: "/assets/sounds/castle.mp3",
  check: "/assets/sounds/check.mp3",
  checkmate: "/assets/sounds/checkmate.webm",
  illegal: "/assets/sounds/illegal.mp3",
  premove: "/assets/sounds/premove.mp3",
  promote: "/assets/sounds/promote.mp3",
  start: "/assets/sounds/start.mp3",
  notify: "/assets/sounds/notify.mp3"
};

function playSound(name) {
  const src = SOUND_FILES[name];
  if (!src) {
    return;
  }
  const audio = new Audio(src);
  audio.volume = 0.55;
  audio.play().catch(() => {});
}

function formatClock(seconds) {
  const safe = Math.max(0, seconds);
  const minutes = Math.floor(safe / 60);
  const secs = safe % 60;
  return `${minutes}:${String(secs).padStart(2, "0")}`;
}

async function apiFetch(path, options = {}) {
  const response = await fetch(`${API_TARGET}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    }
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || "Request failed");
  }
  return data;
}

function App() {
  const [page, setPage] = useState("Home");
  const [authOpen, setAuthOpen] = useState(false);
  const [token, setToken] = useState(() => localStorage.getItem("chess_v2_token") || "");
  const [user, setUser] = useState(null);
  const [botConfig, setBotConfig] = useState(null);
  const [localStats, setLocalStats] = useState(null);

  function refreshLocalStats() {
    return apiFetch("/api/local/stats").then(setLocalStats).catch(() => null);
  }

  useEffect(() => {
    if (!token) {
      setUser(null);
      return;
    }
    apiFetch("/api/auth/me", {
      headers: { Authorization: `Bearer ${token}` }
    })
      .then((data) => setUser(data.user))
      .catch(() => {
        localStorage.removeItem("chess_v2_token");
        setToken("");
      });
  }, [token]);

  useEffect(() => {
    refreshLocalStats();
  }, []);

  function handleAuth(data) {
    localStorage.setItem("chess_v2_token", data.token);
    setToken(data.token);
    setUser(data.user);
    setAuthOpen(false);
  }

  function logout() {
    localStorage.removeItem("chess_v2_token");
    setToken("");
    setUser(null);
  }

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
        <button className="login-button" onClick={() => setPage("Profile")}>
          {localStats?.profile?.username || "Profile"}
        </button>
      </nav>

      {page === "Home" && <HomePage onPlay={() => { setBotConfig(null); setPage("Play"); }} onProfile={() => setPage("Profile")} />}
      {page === "Play" && <PlayPage botConfig={botConfig} />}
      {page === "Bot Battle" && <BotBattlePage onStart={(config) => { setBotConfig(config); setPage("Play"); }} />}
      {page === "Puzzle" && <PuzzlePage />}
      {page === "Analysis" && <AnalysisPage />}
      {page === "Profile" && (
        <ProfilePage
          localStats={localStats}
          onRefresh={refreshLocalStats}
        />
      )}
      {page === "Leaderboard" && <LeaderboardPage localStats={localStats} />}
      {authOpen && <AuthModal onClose={() => setAuthOpen(false)} onAuth={handleAuth} />}
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

function HomePage({ onPlay, onProfile }) {
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
          <button className="secondary-action" onClick={onProfile}>Local profile</button>
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

function PlayPage({ botConfig }) {
  const gameRef = useRef(new Chess());
  const localGamePromise = useRef(null);
  const finishedRef = useRef(false);
  const [board, setBoard] = useState(gameRef.current.board());
  const [selected, setSelected] = useState(null);
  const [legalTargets, setLegalTargets] = useState([]);
  const [moves, setMoves] = useState([]);
  const [captured, setCaptured] = useState({ w: [], b: [] });
  const [premove, setPremove] = useState(null);
  const [timeLeft, setTimeLeft] = useState({ w: INITIAL_CLOCK, b: INITIAL_CLOCK });
  const [gameOver, setGameOver] = useState("");
  const [socketStatus, setSocketStatus] = useState("offline");
  const [chat, setChat] = useState([
    { from: "system", text: "Welcome to CHESS V2." },
    { from: "meme", text: "Capture memes will live here." }
  ]);

  useEffect(() => {
    const wsBase = API_TARGET
      ? API_TARGET.replace(/^http/, "ws")
      : `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}`;
    const ws = new WebSocket(`${wsBase}/ws/game/demo-game`);
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
  const botToMove = botConfig && gameRef.current.turn() === botConfig.color;
  const legalTargetSet = new Set(legalTargets.map((move) => move.to));

  function createLocalGame() {
    const botName = botConfig?.label || "Opponent";
    const whiteName = botConfig?.color === "w" ? botName : "Player";
    const blackName = botConfig?.color === "b" ? botName : "Player";
    localGamePromise.current = apiFetch("/api/local/games", {
      method: "POST",
      body: JSON.stringify({
        white_name: whiteName,
        black_name: blackName,
        mode: botConfig ? "bot" : "local"
      })
    }).catch(() => null);
    finishedRef.current = false;
  }

  useEffect(() => {
    createLocalGame();
    return () => {
      localGamePromise.current = null;
    };
  }, [botConfig]);

  useEffect(() => {
    const clearOnEscape = (event) => {
      if (event.key === "Escape") {
        setSelected(null);
        setLegalTargets([]);
        setPremove(null);
      }
    };
    window.addEventListener("keydown", clearOnEscape);
    return () => window.removeEventListener("keydown", clearOnEscape);
  }, []);

  async function saveMove(move) {
    const game = await localGamePromise.current;
    if (!game) {
      return;
    }
    apiFetch(`/api/local/games/${game.id}/moves`, {
      method: "POST",
      body: JSON.stringify({
        ply: gameRef.current.history().length - 1,
        uci: `${move.from}${move.to}${move.promotion || ""}`,
        san: move.san,
        fen_after: gameRef.current.fen()
      })
    }).catch(() => {});
  }

  async function finishLocalGame(result) {
    if (finishedRef.current) {
      return;
    }
    finishedRef.current = true;
    const game = await localGamePromise.current;
    if (!game) {
      return;
    }
    apiFetch(`/api/local/games/${game.id}/finish`, {
      method: "POST",
      body: JSON.stringify({
        result,
        pgn: gameRef.current.pgn(),
        final_fen: gameRef.current.fen()
      })
    }).catch(() => {});
  }

  useEffect(() => {
    if (gameOver || gameRef.current.isGameOver()) {
      return;
    }
    const timer = window.setInterval(() => {
      const active = gameRef.current.turn();
      setTimeLeft((current) => {
        if (current[active] <= 0) {
          return current;
        }
        const nextValue = Math.max(0, current[active] - 1);
        if (nextValue === 10) {
          playSound("notify");
        }
        if (nextValue === 0) {
          const winner = active === "w" ? "Black" : "White";
          setGameOver(`${winner} wins on time`);
          finishLocalGame(active === "w" ? "0-1" : "1-0");
        }
        return { ...current, [active]: nextValue };
      });
    }, 1000);
    return () => window.clearInterval(timer);
  }, [gameOver, board]);

  function squareName(row, col) {
    return "abcdefgh"[col] + (8 - row);
  }

  function handleSquare(row, col) {
    if (gameOver || gameRef.current.isGameOver()) {
      return;
    }
    const square = squareName(row, col);
    const piece = gameRef.current.get(square);

    if (botToMove) {
      handlePremove(square, piece);
      return;
    }

    if (!selected) {
      if (piece && piece.color === gameRef.current.turn()) {
        selectSquare(square);
      } else if (piece) {
        playSound("illegal");
      }
      return;
    }

    if (selected === square) {
      setSelected(null);
      setLegalTargets([]);
      return;
    }

    const before = gameRef.current.get(square);
    const move = make_move(gameRef.current, { from: selected, to: square, promotion: "q" });
    if (!move) {
      if (piece && piece.color === gameRef.current.turn()) {
        selectSquare(square);
      } else {
        playSound("illegal");
        setSelected(null);
        setLegalTargets([]);
      }
      return;
    }

    commitMove(move, before);
  }

  function clearSelection() {
    setSelected(null);
    setLegalTargets([]);
  }

  function selectSquare(square) {
    setSelected(square);
    setLegalTargets(get_legal_moves(gameRef.current, gameRef.current.turn()).filter((move) => move.from === square));
  }

  function selectSquareForColor(square, color) {
    setSelected(square);
    setLegalTargets(get_legal_moves(gameRef.current, color).filter((move) => move.from === square));
  }

  function handlePremove(square, piece) {
    const humanColor = botConfig?.color === "b" ? "w" : "b";
    if (!selected) {
      if (piece && piece.color === humanColor) {
        selectSquareForColor(square, humanColor);
      } else {
        playSound("illegal");
      }
      return;
    }
    if (selected === square) {
      setSelected(null);
      setLegalTargets([]);
      setPremove(null);
      return;
    }
    if (piece && piece.color === humanColor) {
      selectSquareForColor(square, humanColor);
      return;
    }
    setPremove({ from: selected, to: square });
    setSelected(null);
    setLegalTargets([]);
    playSound("premove");
  }

  function commitMove(move, before = null, options = {}) {
    if (before || move.captured) {
      const capturedColor = move.color === "w" ? "b" : "w";
      const capturedType = move.captured || before?.type;
      setCaptured((state) => ({
        ...state,
        [capturedColor]: [
          ...state[capturedColor],
          `${capturedColor}${pieceCodes[capturedType]}`
        ]
      }));
    }
    if (move.captured || before) {
      playSound("capture");
    } else if (move.flags?.includes("k") || move.flags?.includes("q")) {
      playSound("castle");
    } else {
      playSound("move");
    }
    if (move.promotion) {
      playSound("promote");
    }
    if (gameRef.current.isCheckmate()) {
      playSound("checkmate");
      setGameOver(`${move.color === "w" ? "White" : "Black"} wins by checkmate`);
      finishLocalGame(move.color === "w" ? "1-0" : "0-1");
    } else if (gameRef.current.isCheck()) {
      playSound("check");
    } else if (gameRef.current.isDraw()) {
      setGameOver("Draw");
      finishLocalGame("1/2-1/2");
    }
    setSelected(null);
    setLegalTargets([]);
    if (options.clearPremove !== false) {
      setPremove(null);
    }
    setBoard(gameRef.current.board());
    setMoves(gameRef.current.history({ verbose: true }));
    saveMove(move);
  }

  useEffect(() => {
    if (!botToMove || gameRef.current.isGameOver()) {
      return;
    }
    let cancelled = false;
    const timer = window.setTimeout(async () => {
      const legalMoves = get_legal_moves(gameRef.current, botConfig.color);
      if (!legalMoves.length) {
        return;
      }
      try {
        const chosenMove = await Promise.resolve(
          botConfig.bot.choose_move(gameRef.current, legalMoves, botConfig.color)
        );
        if (cancelled || !chosenMove || gameRef.current.isGameOver()) {
          return;
        }
      const before = gameRef.current.get(chosenMove.to);
      const move = make_move(gameRef.current, chosenMove);
      if (move) {
        commitMove(move, before, { clearPremove: false });
      }
      } catch (error) {
        if (!cancelled) {
          setGameOver(error.message || "Bot move failed");
          playSound("illegal");
        }
      }
    }, 450);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [botToMove, board, botConfig]);

  useEffect(() => {
    if (!premove || !botConfig || botToMove || gameRef.current.isGameOver()) {
      return;
    }
    const legalMoves = get_legal_moves(gameRef.current, gameRef.current.turn());
    const chosenMove = legalMoves.find((move) => move.from === premove.from && move.to === premove.to);
    if (!chosenMove) {
      setPremove(null);
      playSound("illegal");
      return;
    }
    const before = gameRef.current.get(chosenMove.to);
    const move = make_move(gameRef.current, { ...chosenMove, promotion: chosenMove.promotion || "q" });
    if (move) {
      commitMove(move, before);
    }
  }, [premove, botToMove, botConfig, board]);

  function resetGame() {
    gameRef.current = new Chess();
    setBoard(gameRef.current.board());
    setSelected(null);
    setLegalTargets([]);
    setPremove(null);
    setCaptured({ w: [], b: [] });
    setTimeLeft({ w: INITIAL_CLOCK, b: INITIAL_CLOCK });
    setGameOver("");
    setMoves([]);
    createLocalGame();
  }

  async function undoMove() {
    const history = gameRef.current.history({ verbose: true });
    const lastMove = history[history.length - 1];
    gameRef.current.undo();
    const game = await localGamePromise.current;
    if (game) {
      apiFetch(`/api/local/games/${game.id}/moves/last`, { method: "DELETE" }).catch(() => {});
    }
    if (lastMove?.captured) {
      const capturedColor = lastMove.color === "w" ? "b" : "w";
      setCaptured((state) => ({
        ...state,
        [capturedColor]: state[capturedColor].slice(0, -1)
      }));
    }
    setBoard(gameRef.current.board());
    setMoves(gameRef.current.history({ verbose: true }));
    setSelected(null);
    setLegalTargets([]);
    setPremove(null);
    setGameOver("");
    finishedRef.current = false;
  }

  return (
    <section className="page play-layout">
      <div className="board-zone">
        <div className="turn-line">{turn} TO MOVE</div>
        <ChessBoard
          board={board}
          selected={selected}
          premove={premove}
          legalTargets={legalTargetSet}
          onSquare={handleSquare}
          onClearSelection={clearSelection}
        />
      </div>
      <aside className="game-panel">
        <h2>CHESS V2</h2>
        {botConfig && <div className="socket-pill">Bot: {botConfig.label}</div>}
        <div className="socket-pill">Realtime: {socketStatus}</div>
        {gameOver && <div className="socket-pill danger-pill">{gameOver}</div>}
        <TimerBlock label="BLACK" time={formatClock(timeLeft.b)} active={turn === "BLACK"} />
        <TimerBlock label="WHITE" time={formatClock(timeLeft.w)} active={turn === "WHITE"} />
        <CapturedPieces captured={captured} />
        <MoveHistory moves={moveHistory} />
        <div className="action-row">
          <button onClick={() => {
            const humanColor = botConfig?.color === "w" ? "b" : "w";
            setGameOver("You resigned");
            finishLocalGame(humanColor === "w" ? "0-1" : "1-0");
          }}>Resign</button>
          <button onClick={() => { setGameOver("Draw agreed"); finishLocalGame("1/2-1/2"); }}>Draw</button>
          <button onClick={undoMove}>Undo</button>
          <button onClick={resetGame}>Reset</button>
        </div>
        <ChatPanel chat={chat} />
      </aside>
    </section>
  );
}

function ChessBoard({ board, selected, premove, legalTargets, onSquare, onClearSelection }) {
  return (
    <div className="chess-board" onContextMenu={(event) => { event.preventDefault(); onClearSelection?.(); }}>
      {board.flatMap((row, rowIndex) =>
        row.map((piece, colIndex) => {
          const square = "abcdefgh"[colIndex] + (8 - rowIndex);
          const isLight = (rowIndex + colIndex) % 2 === 0;
          const isSelected = selected === square;
          const isPremove = premove && (premove.from === square || premove.to === square);
          const isLegal = legalTargets.has(square);
          const isCaptureTarget = isLegal && piece;
          return (
            <button
              className={[
                "square",
                isLight ? "light" : "dark",
                isSelected ? "selected" : "",
                isPremove ? "premove" : "",
                isLegal ? "legal-target" : "",
                isCaptureTarget ? "capture-target" : ""
              ].join(" ")}
              key={square}
              onClick={() => onSquare(rowIndex, colIndex)}
            >
              {piece && (
                <img
                  className="piece-img"
                  src={`/assets/pieces/${piece.color}${pieceCodes[piece.type]}.png`}
                  alt={`${piece.color === "w" ? "White" : "Black"} ${piece.type}`}
                  draggable="false"
                />
              )}
              {isLegal && !piece && <span className="legal-dot" />}
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
      <CapturedRow label="White captured" pieces={captured.b} />
      <CapturedRow label="Black captured" pieces={captured.w} />
    </section>
  );
}

function CapturedRow({ label, pieces }) {
  return (
    <div className="captured-row">
      <span>{label}:</span>
      <div className="captured-pieces">
        {pieces.length ? pieces.map((piece, index) => (
          <img src={`/assets/pieces/${piece}.png`} alt={piece} key={`${piece}-${index}`} />
        )) : <span>none</span>}
      </div>
    </div>
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

function AuthModal({ onClose, onAuth }) {
  const [mode, setMode] = useState("login");
  const [error, setError] = useState("");
  const [form, setForm] = useState({
    login: "",
    username: "",
    email: "",
    password: "",
    display_name: "",
    favorite_theme: "Royal cosmic"
  });

  useEffect(() => {
    if (!GOOGLE_CLIENT_ID || mode !== "login") {
      return;
    }
    const scriptId = "google-identity-script";
    if (!document.getElementById(scriptId)) {
      const script = document.createElement("script");
      script.id = scriptId;
      script.src = "https://accounts.google.com/gsi/client";
      script.async = true;
      document.head.appendChild(script);
    }
  }, [mode]);

  function update(key, value) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function submit(event) {
    event.preventDefault();
    setError("");
    try {
      const path = mode === "login" ? "/api/auth/login" : "/api/auth/register";
      const payload = mode === "login"
        ? { login: form.login, password: form.password }
        : {
            username: form.username,
            email: form.email,
            password: form.password,
            display_name: form.display_name || null,
            favorite_theme: form.favorite_theme || null
          };
      const data = await apiFetch(path, {
        method: "POST",
        body: JSON.stringify(payload)
      });
      onAuth(data);
    } catch (err) {
      setError(err.message);
    }
  }

  async function googleSignIn() {
    setError("");
    if (!GOOGLE_CLIENT_ID) {
      setError("Add VITE_GOOGLE_CLIENT_ID and GOOGLE_CLIENT_ID to enable Google auth.");
      return;
    }
    if (!window.google?.accounts?.id) {
      setError("Google auth is still loading. Try again in a second.");
      return;
    }
    window.google.accounts.id.initialize({
      client_id: GOOGLE_CLIENT_ID,
      callback: async (response) => {
        try {
          const data = await apiFetch("/api/auth/google", {
            method: "POST",
            body: JSON.stringify({ credential: response.credential })
          });
          onAuth(data);
        } catch (err) {
          setError(err.message);
        }
      }
    });
    window.google.accounts.id.prompt();
  }

  return (
    <div className="modal-backdrop">
      <section className="auth-modal">
        <button className="modal-close" onClick={onClose}>×</button>
        <h2>{mode === "login" ? "Login" : "Register"}</h2>
        <div className="auth-tabs">
          <button className={mode === "login" ? "active" : ""} onClick={() => setMode("login")}>Login</button>
          <button className={mode === "register" ? "active" : ""} onClick={() => setMode("register")}>Register</button>
        </div>
        <form className="auth-form" onSubmit={submit}>
          {mode === "login" ? (
            <label>
              Username or email
              <input value={form.login} onChange={(event) => update("login", event.target.value)} required />
            </label>
          ) : (
            <>
              <label>
                Username
                <input value={form.username} onChange={(event) => update("username", event.target.value)} required />
              </label>
              <label>
                Email
                <input type="email" value={form.email} onChange={(event) => update("email", event.target.value)} required />
              </label>
              <label>
                Display name optional
                <input value={form.display_name} onChange={(event) => update("display_name", event.target.value)} />
              </label>
            </>
          )}
          <label>
            Password
            <input type="password" value={form.password} onChange={(event) => update("password", event.target.value)} required />
          </label>
          {error && <p className="form-error">{error}</p>}
          <button className="primary-action" type="submit">{mode === "login" ? "Login" : "Create account"}</button>
        </form>
        <button className="google-button" onClick={googleSignIn}>Continue with Google</button>
      </section>
    </div>
  );
}

function BotBattlePage({ onStart }) {
  const [botKey, setBotKey] = useState("random");
  const [level, setLevel] = useState(1);
  const [personality, setPersonality] = useState("gambler");
  const [botColor, setBotColor] = useState("b");
  const selectedBot = BOT_DEFINITIONS[botKey];

  return (
    <section className="page tool-layout">
      <h1>Bot Battle</h1>
      <div className="tool-grid">
        <article className="tool-panel">
          <h3>Choose bot level</h3>
          <select value={botKey} onChange={(event) => { setBotKey(event.target.value); setLevel(1); }}>
            {Object.entries(BOT_DEFINITIONS).map(([key, bot]) => (
              <option value={key} key={key}>{bot.label}</option>
            ))}
          </select>
          <p>{selectedBot.description}</p>
        </article>
        <article className="tool-panel">
          <h3>Difficulty</h3>
          <select value={level} onChange={(event) => setLevel(Number(event.target.value))}>
            {botKey === "stockfish"
              ? STOCKFISH_LEVELS.map((option) => <option value={option.value} key={option.value}>{option.label}</option>)
              : Object.keys(BOT_LEVELS).map((botLevel) => <option value={botLevel} key={botLevel}>Level {botLevel}</option>)}
          </select>
          <p>{botKey === "stockfish" ? "Uses the local Stockfish skill setting." : "Higher levels make fewer random moves."}</p>
        </article>
        <article className="tool-panel">
          <h3>Choose bot personality</h3>
          <select value={personality} onChange={(event) => setPersonality(event.target.value)}>
            {Object.entries(BOT_PERSONALITIES).map(([key, botPersonality]) => (
              <option value={key} key={key}>{botPersonality.label}</option>
            ))}
          </select>
        </article>
        <article className="tool-panel">
          <h3>Choose side</h3>
          <select value={botColor} onChange={(event) => setBotColor(event.target.value)}>
            <option value="b">You play White</option>
            <option value="w">You play Black</option>
          </select>
        </article>
        <article className="tool-panel">
          <h3>Start game</h3>
          <p>{botColor === "b" ? "You play white. The bot plays black." : "The bot plays white. You play black."}</p>
          <button
            className="primary-action"
            onClick={() => onStart({
              bot: selectedBot.create(level, personality),
              label: selectedBot.label,
              key: botKey,
              level,
              personality,
              color: botColor
            })}
          >
            Start bot battle
          </button>
        </article>
      </div>
    </section>
  );
}

function PuzzlePage() {
  const managerRef = useRef(new PuzzleManager());
  const [puzzles, setPuzzles] = useState([]);
  const [currentPuzzle, setCurrentPuzzle] = useState(null);
  const [board, setBoard] = useState(new Chess().board());
  const [selected, setSelected] = useState(null);
  const [legalTargets, setLegalTargets] = useState([]);
  const [feedback, setFeedback] = useState("Choose a puzzle to begin.");
  const [attempts, setAttempts] = useState(0);
  const [showHint, setShowHint] = useState(false);
  const [complete, setComplete] = useState(false);
  const legalTargetSet = new Set(legalTargets.map((move) => move.to));
  const categories = [...new Set(puzzles.flatMap((puzzle) => puzzle.themes || []))];

  useEffect(() => {
    loadPuzzles()
      .then((loadedPuzzles) => {
        setPuzzles(loadedPuzzles);
        managerRef.current = new PuzzleManager(loadedPuzzles);
        if (loadedPuzzles.length) {
          startPuzzle(loadedPuzzles[0].id, loadedPuzzles);
        } else {
          setFeedback("No validated puzzles have been imported yet.");
        }
      })
      .catch((error) => setFeedback(error.message));
  }, []);

  function startPuzzle(puzzleId, sourcePuzzles = puzzles) {
    const manager = new PuzzleManager(sourcePuzzles);
    const puzzle = manager.start_puzzle(puzzleId);
    managerRef.current = manager;
    setCurrentPuzzle(puzzle);
    setBoard(manager.game.board());
    setSelected(null);
    setLegalTargets([]);
    setAttempts(0);
    setShowHint(false);
    setComplete(false);
    setFeedback("Find the forcing move.");
    playSound("start");
  }

  function squareName(row, col) {
    return "abcdefgh"[col] + (8 - row);
  }

  function selectPuzzleSquare(square) {
    const manager = managerRef.current;
    setSelected(square);
    setLegalTargets(manager.legal_moves().filter((move) => move.from === square));
  }

  function handlePuzzleSquare(row, col) {
    const manager = managerRef.current;
    if (!manager.game || complete) {
      return;
    }
    const square = squareName(row, col);
    const piece = manager.game.get(square);

    if (!selected) {
      if (piece && piece.color === manager.game.turn()) {
        selectPuzzleSquare(square);
      }
      return;
    }

    if (selected === square) {
      setSelected(null);
      setLegalTargets([]);
      return;
    }

    const result = manager.check_move({ from: selected, to: square, promotion: "q" });
    setAttempts((count) => count + 1);
    const attemptNumber = attempts + 1;
    setSelected(null);
    setLegalTargets([]);

    if (!result.ok || result.complete) {
      apiFetch("/api/local/puzzle-attempts", {
        method: "POST",
        body: JSON.stringify({
          puzzle_id: currentPuzzle.id,
          correct: result.complete,
          attempts: attemptNumber,
          puzzle_rating: currentPuzzle.rating || null,
          themes: currentPuzzle.themes || []
        })
      }).catch(() => {});
    }

    if (!result.ok) {
      setFeedback("Not quite. Look for a forcing move: check, capture, or threat.");
      playSound("illegal");
      return;
    }

    playSound(result.complete ? "checkmate" : "move");
    setBoard(manager.game.board());

    if (result.complete) {
      setComplete(true);
      setFeedback("Puzzle solved.");
      return;
    }

    setFeedback("Correct. Forced reply incoming.");
    window.setTimeout(() => {
      const reply = manager.play_forced_reply();
      if (reply) {
        playSound(reply.captured ? "capture" : "move");
        setBoard(manager.game.board());
        setFeedback("Now find the next winning move.");
      }
      if (manager.is_complete()) {
        setComplete(true);
        setFeedback("Puzzle solved.");
      }
    }, 450);
  }

  function nextPuzzle() {
    if (!puzzles.length || !currentPuzzle) {
      return;
    }
    const currentIndex = puzzles.findIndex((puzzle) => puzzle.id === currentPuzzle.id);
    const next = puzzles[(currentIndex + 1) % puzzles.length];
    startPuzzle(next.id);
  }

  return (
    <section className="page tool-layout">
      <h1>Puzzle</h1>
      <div className="puzzle-layout">
        <div className="puzzle-board-zone">
          <ChessBoard
            board={board}
            selected={selected}
            premove={null}
            legalTargets={legalTargetSet}
            onSquare={handlePuzzleSquare}
          />
        </div>
        <aside className="game-panel puzzle-panel">
          <h2>{currentPuzzle?.title || "Validated puzzles"}</h2>
          <div className="puzzle-meta">
            <span>Rating {currentPuzzle?.rating || "-"}</span>
            <span>{currentPuzzle ? new Chess(currentPuzzle.solver_fen).turn() === "w" ? "white to move" : "black to move" : "-"}</span>
            <span>Attempts {attempts}</span>
          </div>
          <div className="tag-row">
            {(currentPuzzle?.themes || []).map((tag) => <span key={tag}>{tag}</span>)}
          </div>
          <p className={complete ? "feedback-good" : "feedback-line"}>{feedback}</p>
          {showHint && <p className="hint-box">{currentPuzzle?.hint}</p>}
          {complete && <p className="explanation-box">{currentPuzzle?.explanation}</p>}
          <div className="puzzle-actions">
            <button onClick={() => setShowHint(true)}>Hint</button>
            <button onClick={nextPuzzle}>Next puzzle</button>
          </div>
          <section className="panel-section">
            <h3>Puzzle categories</h3>
            <div className="category-grid">
              {categories.map((category) => (
                <button
                  key={category}
                  onClick={() => {
                    const match = puzzles.find((puzzle) => puzzle.themes?.includes(category));
                    if (match) {
                      startPuzzle(match.id);
                    }
                  }}
                >
                  {category}
                </button>
              ))}
            </div>
          </section>
          <section className="panel-section">
            <h3>Puzzle list</h3>
            <div className="puzzle-list">
              {puzzles.map((puzzle) => (
                <button
                  className={currentPuzzle?.id === puzzle.id ? "active" : ""}
                  key={puzzle.id}
                  onClick={() => startPuzzle(puzzle.id)}
                >
                  {puzzle.title}
                </button>
              ))}
            </div>
          </section>
        </aside>
      </div>
    </section>
  );
}

function AnalysisPage() {
  return (
    <section className="page tool-layout">
      <h1>Analysis</h1>
      <div className="analysis-layout">
        <article className="tool-panel">
          <h3>Upload PGN</h3>
          <textarea placeholder="Paste PGN here" />
          <button className="primary-action">Analyze game</button>
        </article>
        <article className="tool-panel">
          <h3>Mistakes / blunders</h3>
          <div className="analysis-list">
            <p>No analysis yet.</p>
          </div>
        </article>
      </div>
    </section>
  );
}

function ProfilePage({ localStats, onRefresh }) {
  const identity = localStats?.profile || { id: 1, username: "Player" };
  const [players, setPlayers] = useState([]);
  const [username, setUsername] = useState(identity.username || "");
  const [newUsername, setNewUsername] = useState("");
  const [message, setMessage] = useState("");

  async function loadPlayers() {
    try {
      const data = await apiFetch("/api/local/players");
      setPlayers(data.players || []);
    } catch (error) {
      setMessage(error.message);
    }
  }

  useEffect(() => {
    setUsername(identity.username || "");
  }, [identity.id, identity.username]);

  useEffect(() => {
    loadPlayers();
  }, [identity.id]);

  async function saveProfile(event) {
    event.preventDefault();
    setMessage("");
    try {
      await apiFetch("/api/local/profile", {
        method: "PUT",
        body: JSON.stringify({ username })
      });
      await onRefresh();
      await loadPlayers();
      setMessage("Profile saved.");
    } catch (error) {
      setMessage(error.message);
    }
  }

  async function createNewPlayer() {
    setMessage("");
    try {
      if (!newUsername.trim()) {
        throw new Error("Enter a username for the new player.");
      }
      await apiFetch("/api/local/players", {
        method: "POST",
        body: JSON.stringify({ username: newUsername })
      });
      setNewUsername("");
      await onRefresh();
      await loadPlayers();
      setMessage("New player created and activated.");
    } catch (error) {
      setMessage(error.message);
    }
  }

  async function switchPlayer(event) {
    const playerId = Number(event.target.value);
    if (!playerId || playerId === identity.id) {
      return;
    }
    try {
      await apiFetch(`/api/local/players/${playerId}/activate`, { method: "POST" });
      await onRefresh();
      await loadPlayers();
      setMessage("Active player switched.");
    } catch (error) {
      setMessage(error.message);
    }
  }

  const games = localStats?.recent_games || [];
  const puzzles = localStats?.recent_puzzles || [];
  const percent = Math.round((localStats?.puzzle_accuracy || 0) * 100);

  return (
    <section className="page profile-layout">
      <h1>Profile</h1>
      <p className="profile-kicker">Local player memory · saved on this computer</p>
      <div className="profile-grid">
        <form className="profile-card profile-form" onSubmit={saveProfile}>
          <h3>Local profile</h3>
          <p className="profile-muted">Active player: {identity.username}</p>
          <label>
            Username
            <input value={username} maxLength={24} onChange={(event) => setUsername(event.target.value)} />
          </label>
          <div className="profile-actions">
            <button className="primary-action" type="submit">Save profile</button>
          </div>
          <div className="profile-divider" />
          <label>
            New player
            <input value={newUsername} maxLength={24} placeholder="Enter a username" onChange={(event) => setNewUsername(event.target.value)} />
          </label>
          <button className="secondary-action" type="button" onClick={createNewPlayer}>Create and switch</button>
          <label>
            Switch player
            <select value={identity.id} onChange={switchPlayer}>
              {players.map((player) => <option value={player.id} key={player.id}>{player.username}</option>)}
            </select>
          </label>
          {message && <p className="form-message">{message}</p>}
        </form>

        <div className="profile-card profile-summary-card">
          <h3>{identity.username}</h3>
          <p>Created: {identity.created_at || "Today"}</p>
          <p>Last active: {identity.last_active_at || "Now"}</p>
          <div className="profile-stat-grid">
            <ProfileStat label="Games played" value={localStats?.games_played ?? 0} />
            <ProfileStat label="Win rate" value={`${Math.round((localStats?.win_rate || 0) * 100)}%`} />
            <ProfileStat label="Puzzle accuracy" value={`${percent}%`} />
            <ProfileStat label="Solved" value={localStats?.puzzles_solved ?? 0} />
          </div>
        </div>
      </div>

      <div className="profile-grid profile-detail-grid">
        <div className="profile-card">
          <h3>Game stats</h3>
          <p>Games played: {localStats?.games_played ?? 0}</p>
          <p>Wins: {localStats?.wins ?? 0}</p>
          <p>Losses: {localStats?.losses ?? 0}</p>
          <p>Draws: {localStats?.draws ?? 0}</p>
          <p>Unfinished: {localStats?.unfinished_games ?? 0}</p>
        </div>
        <div className="profile-card">
          <h3>Bot stats</h3>
          <p>Bot games: {localStats?.bot_games ?? 0}</p>
          <p>Bot wins: {localStats?.bot_wins ?? 0}</p>
          <p>Bot losses: {localStats?.bot_losses ?? 0}</p>
          <p>Bot draws: {localStats?.bot_draws ?? 0}</p>
          <p>Best bot beaten: {localStats?.best_bot_beaten || "None yet"}</p>
        </div>
        <div className="profile-card">
          <h3>Puzzle stats</h3>
          <p>Attempts: {localStats?.puzzle_attempts ?? 0}</p>
          <p>Solved: {localStats?.puzzles_solved ?? 0}</p>
          <p>Accuracy: {percent}%</p>
          <p>Average attempts: {localStats?.average_puzzle_attempts ?? 0}</p>
          <p>Best rating solved: {localStats?.best_puzzle_rating_solved || "None yet"}</p>
        </div>
      </div>

      <div className="profile-grid profile-detail-grid">
        <div className="profile-card profile-activity-card">
          <h3>Recent games</h3>
          {games.length ? games.map((game) => (
            <div className="activity-row" key={game.id}>
              <strong className={`result-${game.player_result}`}>{game.player_result}</strong>
              <span>vs {game.opponent_display || "Opponent"} · {game.total_moves || 0} moves</span>
              <small>{game.result_reason || game.mode || "game"} · {game.date || "recently"}</small>
            </div>
          )) : <p>No completed games yet.</p>}
        </div>
        <div className="profile-card profile-activity-card">
          <h3>Recent puzzle attempts</h3>
          {puzzles.length ? puzzles.map((attempt) => (
            <div className="activity-row" key={attempt.id}>
              <strong className={attempt.solved ? "result-win" : "result-loss"}>{attempt.solved ? "Solved" : "Failed"}</strong>
              <span>{attempt.puzzle_id} · {attempt.attempts} attempt{attempt.attempts === 1 ? "" : "s"}</span>
              <small>{attempt.puzzle_rating || "Unrated"} · {(attempt.themes || []).join(", ") || "untagged"}</small>
            </div>
          )) : <p>No puzzle attempts yet.</p>}
        </div>
      </div>
    </section>
  );
}

function ProfileStat({ label, value }) {
  return (
    <div className="profile-stat">
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  );
}

function LeaderboardPage() {
  const [entries, setEntries] = useState([]);

  useEffect(() => {
    apiFetch("/api/local/leaderboard").then(setEntries).catch(() => setEntries([]));
  }, []);

  return (
    <section className="page tool-layout">
      <h1>Leaderboard</h1>
      <div className="leaderboard-grid">
        {entries.length ? entries.map((entry) => (
          <article className="tool-panel" key={entry.category}>
            <h3>{entry.category}</h3>
            {entry.entries?.length ? (
              <ol className="leaderboard-list">
                {entry.entries.map((player) => (
                  <li key={player.player_id}>
                    <span>{player.username}</span>
                    <strong>{player.score}{entry.category.includes("accuracy") ? "%" : ""}</strong>
                  </li>
                ))}
              </ol>
            ) : <p>No local results yet.</p>}
          </article>
        )) : <article className="tool-panel"><p>No local results yet.</p></article>}
      </div>
    </section>
  );
}

createRoot(document.getElementById("root")).render(<App />);
