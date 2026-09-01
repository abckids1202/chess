import React, { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { Chess } from "chess.js";
import { BOT_DEFINITIONS, BOT_LEVELS, BOT_PERSONALITIES, STOCKFISH_LEVELS } from "./bots";
import { get_legal_moves, make_move } from "./chessEngine";
import {
  PuzzleManager,
  loadPuzzles,
  puzzleDisplayExplanation,
  puzzleDisplayTitle,
  puzzleThemeLabels
} from "./puzzleManager";
import { BackToTop, CommandPalette, HomePage, ScrollProgress, TopNav } from "./homeComponents";
import "./styles.css";

const API_TARGET = (import.meta.env.VITE_API_TARGET || "").replace(/\/$/, "");

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || "";
const pieceCodes = { p: "P", n: "N", b: "B", r: "R", q: "Q", k: "K" };
const INITIAL_CLOCK = 10 * 60;
const MATCH_INTENTIONS = [
  { value: "none", label: "Play freely" },
  { value: "castle_early", label: "Castle early" },
  { value: "develop_first", label: "Develop before attacking" },
  { value: "protect_my_queen", label: "Protect my queen" },
  { value: "slow_down", label: "Slow down and look twice" }
];
const MATCH_REFLECTIONS = [
  { value: "experimenting", label: "I was experimenting" },
  { value: "learning", label: "I was learning" },
  { value: "patient", label: "I played patiently" },
  { value: "panicked", label: "I panicked" },
  { value: "fun", label: "Just playing for fun" }
];
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
  const [analysisGameId, setAnalysisGameId] = useState("");
  const [commandOpen, setCommandOpen] = useState(false);

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

  useEffect(() => {
    const handleShortcuts = (event) => {
      const target = event.target;
      const isTyping = target instanceof HTMLElement &&
        ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName);
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setCommandOpen(true);
      } else if (event.key === "/" && !isTyping) {
        event.preventDefault();
        setCommandOpen(true);
      }
    };
    window.addEventListener("keydown", handleShortcuts);
    return () => window.removeEventListener("keydown", handleShortcuts);
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

  function openAnalysis(gameId = "") {
    setAnalysisGameId(gameId ? String(gameId) : "");
    setPage("Analysis");
  }

  function navigateToPage(nextPage) {
    if (nextPage === "Play") {
      setBotConfig(null);
    }
    setPage(nextPage);
  }

  return (
    <main className="app-shell">
      <Starfield />
      <ScrollProgress />
      <TopNav
        page={page}
        onNavigate={navigateToPage}
        username={localStats?.profile?.username || "Profile"}
        onOpenCommand={() => setCommandOpen(true)}
      />

      <div className="page-stage" key={page}>
        {page === "Home" && (
          <HomePage
            apiFetch={apiFetch}
            localStats={localStats}
            onRefreshStats={refreshLocalStats}
            onPlay={() => navigateToPage("Play")}
            onProfile={() => navigateToPage("Profile")}
            onNavigate={navigateToPage}
            onOpenAnalysis={openAnalysis}
          />
        )}
        {page === "Play" && <PlayPage botConfig={botConfig} onOpenAnalysis={openAnalysis} />}
        {page === "Bot Battle" && <BotBattlePage onStart={(config) => { setBotConfig(config); setPage("Play"); }} />}
        {page === "Puzzle" && <PuzzlePage />}
        {page === "Analysis" && <AnalysisPage initialGameId={analysisGameId} />}
        {page === "Profile" && (
          <ProfilePage
            localStats={localStats}
            onRefresh={refreshLocalStats}
            onOpenAnalysis={openAnalysis}
          />
        )}
        {page === "Leaderboard" && <LeaderboardPage localStats={localStats} />}
      </div>
      {authOpen && <AuthModal onClose={() => setAuthOpen(false)} onAuth={handleAuth} />}
      <CommandPalette open={commandOpen} onClose={() => setCommandOpen(false)} onNavigate={navigateToPage} />
      <BackToTop />
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

function PlayPage({ botConfig, onOpenAnalysis }) {
  const gameRef = useRef(new Chess());
  const localGamePromise = useRef(null);
  const moveSaveChain = useRef(Promise.resolve());
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
  const [flipOffset, setFlipOffset] = useState(false);
  const [localGameId, setLocalGameId] = useState(null);
  const [gameIntention, setGameIntention] = useState("none");
  const [reflection, setReflection] = useState("");
  const [reflectionNote, setReflectionNote] = useState("");
  const [reflectionSaved, setReflectionSaved] = useState(false);
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
  const boardFlipped = botConfig ? flipOffset : (turn === "BLACK") !== flipOffset;
  const legalTargetSet = new Set(legalTargets.map((move) => move.to));

  function createLocalGame(nextIntention = gameIntention) {
    const botName = botConfig?.label || "Opponent";
    const whiteName = botConfig?.color === "w" ? botName : "Player";
    const blackName = botConfig?.color === "b" ? botName : "Player";
    const request = apiFetch("/api/local/games", {
      method: "POST",
      body: JSON.stringify({
        white_name: whiteName,
        black_name: blackName,
        mode: botConfig ? "bot" : "local",
        time_control: "10+0",
        intention: nextIntention === "none" ? null : nextIntention
      })
    });
    localGamePromise.current = request
      .then((game) => {
        setLocalGameId(game?.id || null);
        return game;
      })
      .catch(() => null);
    moveSaveChain.current = Promise.resolve();
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

  function saveMove(move) {
    const currentGamePromise = localGamePromise.current;
    const ply = gameRef.current.history().length;
    const fenAfter = gameRef.current.fen();
    const saveRequest = async () => {
      const game = await currentGamePromise;
      if (!game) {
        return;
      }
      await apiFetch(`/api/local/games/${game.id}/moves`, {
        method: "POST",
        body: JSON.stringify({
          ply,
          uci: `${move.from}${move.to}${move.promotion || ""}`,
          san: move.san,
          fen_after: fenAfter,
          time_left: timeLeft[move.color]
        })
      }).catch(() => {});
    };
    moveSaveChain.current = moveSaveChain.current.then(saveRequest, saveRequest);
    return moveSaveChain.current;
  }

  async function finishLocalGame(result, resultReason = "manual") {
    if (finishedRef.current) {
      return;
    }
    finishedRef.current = true;
    setReflectionSaved(false);
    const game = await localGamePromise.current;
    if (!game) {
      return;
    }
    await moveSaveChain.current;
    apiFetch(`/api/local/games/${game.id}/finish`, {
      method: "POST",
      body: JSON.stringify({
        result,
        result_reason: resultReason,
        pgn: gameRef.current.pgn(),
        final_fen: gameRef.current.fen()
      })
    }).catch(() => {});
  }

  async function saveIntention(value) {
    setGameIntention(value);
    const game = await localGamePromise.current;
    if (!game) {
      return;
    }
    apiFetch(`/api/local/games/${game.id}`, {
      method: "PATCH",
      body: JSON.stringify({ intention: value === "none" ? null : value })
    }).catch(() => {});
  }

  async function saveReflection() {
    const game = await localGamePromise.current;
    if (!game || !reflection) {
      return;
    }
    try {
      await apiFetch(`/api/local/games/${game.id}/reflection`, {
        method: "POST",
        body: JSON.stringify({
          intention: gameIntention === "none" ? null : gameIntention,
          feeling: reflection,
          note: reflectionNote
        })
      });
      setReflectionSaved(true);
    } catch {
      setReflectionSaved(false);
    }
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
          finishLocalGame(active === "w" ? "0-1" : "1-0", "timeout");
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
    saveMove(move);
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
      finishLocalGame(move.color === "w" ? "1-0" : "0-1", "checkmate");
    } else if (gameRef.current.isCheck()) {
      playSound("check");
    } else if (gameRef.current.isDraw()) {
      setGameOver("Draw");
      finishLocalGame("1/2-1/2", "draw");
    }
    setSelected(null);
    setLegalTargets([]);
    if (options.clearPremove !== false) {
      setPremove(null);
    }
    setBoard(gameRef.current.board());
    setMoves(gameRef.current.history({ verbose: true }));
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
    setFlipOffset(false);
    setCaptured({ w: [], b: [] });
    setTimeLeft({ w: INITIAL_CLOCK, b: INITIAL_CLOCK });
    setGameOver("");
    setMoves([]);
    setGameIntention("none");
    setReflection("");
    setReflectionNote("");
    setReflectionSaved(false);
    createLocalGame("none");
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
          flipped={boardFlipped}
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
        <section className="panel-section intention-panel">
          <h3>Match intention</h3>
          <select
            value={gameIntention}
            disabled={moveHistory.length > 0 || Boolean(gameOver)}
            onChange={(event) => saveIntention(event.target.value)}
          >
            {MATCH_INTENTIONS.map((item) => <option value={item.value} key={item.value}>{item.label}</option>)}
          </select>
          <p>Optional. Give this game one small purpose.</p>
        </section>
        <CapturedPieces captured={captured} />
        <MoveHistory moves={moveHistory} />
        <div className="action-row">
          <button onClick={() => {
            const humanColor = botConfig?.color === "w" ? "b" : "w";
            setGameOver("You resigned");
            finishLocalGame(humanColor === "w" ? "0-1" : "1-0", "resignation");
          }}>Resign</button>
          <button onClick={() => { setGameOver("Draw agreed"); finishLocalGame("1/2-1/2", "agreement"); }}>Draw</button>
          <button onClick={undoMove}>Undo</button>
          <button onClick={resetGame}>Reset</button>
          <button onClick={() => setFlipOffset((value) => !value)}>Flip</button>
        </div>
        <ChatPanel chat={chat} />
        {gameOver && (
          <ReflectionPanel
            reflection={reflection}
            note={reflectionNote}
            saved={reflectionSaved}
            onReflection={setReflection}
            onNote={setReflectionNote}
            onSave={saveReflection}
            onOpenAnalysis={() => onOpenAnalysis?.(localGameId)}
            canOpenAnalysis={Boolean(localGameId)}
          />
        )}
      </aside>
    </section>
  );
}

function ChessBoard({ board, flipped = false, selected, premove, legalTargets, onSquare, onClearSelection }) {
  return (
    <div className="chess-board" onContextMenu={(event) => { event.preventDefault(); onClearSelection?.(); }}>
      {Array.from({ length: 8 }).flatMap((_, displayRow) =>
        Array.from({ length: 8 }).map((__, displayCol) => {
          const rowIndex = flipped ? 7 - displayRow : displayRow;
          const colIndex = flipped ? 7 - displayCol : displayCol;
          const piece = board[rowIndex][colIndex];
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

function ReflectionPanel({
  reflection,
  note,
  saved,
  onReflection,
  onNote,
  onSave,
  onOpenAnalysis,
  canOpenAnalysis
}) {
  return (
    <section className="panel-section reflection-panel">
      <h3>Keep a note from this game</h3>
      <p>Your reflection is saved with this private match.</p>
      <div className="reflection-options">
        {MATCH_REFLECTIONS.map((item) => (
          <button
            type="button"
            key={item.value}
            className={`reflection-option ${reflection === item.value ? "active" : ""}`}
            onClick={() => onReflection(item.value)}
          >
            {item.label}
          </button>
        ))}
      </div>
      <input
        className="reflection-note"
        value={note}
        maxLength={500}
        onChange={(event) => onNote(event.target.value)}
        placeholder="Optional note about the game"
      />
      <div className="reflection-actions">
        <button className="primary-action" type="button" disabled={!reflection} onClick={onSave}>
          {saved ? "Reflection saved" : "Save reflection"}
        </button>
        <button type="button" disabled={!canOpenAnalysis} onClick={onOpenAnalysis}>Open Chronicle</button>
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
    favorite_theme: "Dark fantasy"
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
  const advanceTimerRef = useRef(null);
  const [puzzles, setPuzzles] = useState([]);
  const [currentPuzzle, setCurrentPuzzle] = useState(null);
  const [board, setBoard] = useState(new Chess().board());
  const [selected, setSelected] = useState(null);
  const [legalTargets, setLegalTargets] = useState([]);
  const [feedback, setFeedback] = useState("Choose a puzzle to begin.");
  const [attempts, setAttempts] = useState(0);
  const [showHint, setShowHint] = useState(false);
  const [complete, setComplete] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");
  const legalTargetSet = new Set(legalTargets.map((move) => move.to));
  const currentPuzzleIndex = puzzles.findIndex((puzzle) => puzzle.id === currentPuzzle?.id);

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

    return () => {
      if (advanceTimerRef.current) {
        window.clearTimeout(advanceTimerRef.current);
      }
    };
  }, []);

  function startPuzzle(puzzleId, sourcePuzzles = puzzles) {
    if (advanceTimerRef.current) {
      window.clearTimeout(advanceTimerRef.current);
      advanceTimerRef.current = null;
    }
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
    setSuccessMessage("");
    setFeedback("Find the forcing move.");
    playSound("start");
  }

  function completePuzzle() {
    if (complete) {
      return;
    }
    setComplete(true);
    setSuccessMessage("Good job");
    setFeedback("Trial complete. Loading the next encounter...");
    playSound("notify");
    if (advanceTimerRef.current) {
      window.clearTimeout(advanceTimerRef.current);
    }
    advanceTimerRef.current = window.setTimeout(() => {
      advanceTimerRef.current = null;
      if (!puzzles.length || !currentPuzzle) {
        return;
      }
      const nextIndex = (currentPuzzleIndex + 1 + puzzles.length) % puzzles.length;
      startPuzzle(puzzles[nextIndex].id, puzzles);
    }, 950);
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
      completePuzzle();
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
        completePuzzle();
      }
    }, 450);
  }

  function nextPuzzle() {
    if (!puzzles.length || !currentPuzzle) {
      return;
    }
    const currentIndex = puzzles.findIndex((puzzle) => puzzle.id === currentPuzzle.id);
    const next = puzzles[(currentIndex + 1 + puzzles.length) % puzzles.length];
    startPuzzle(next.id, puzzles);
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
          <div className="puzzle-heading-row">
            <h2>{currentPuzzle ? puzzleDisplayTitle(currentPuzzle, currentPuzzleIndex) : "Validated trials"}</h2>
          </div>
          <p className={complete ? "feedback-good" : "feedback-line"}>{feedback}</p>
          {showHint && <p className="hint-box">{currentPuzzle?.hint}</p>}
          {complete && <p className="explanation-box">{puzzleDisplayExplanation(currentPuzzle)}</p>}
          <div className="puzzle-actions">
            <button onClick={() => setShowHint(true)}>Hint</button>
            <button onClick={nextPuzzle}>Next puzzle</button>
          </div>
        </aside>
      </div>
      {successMessage && (
        <div className="puzzle-success" role="status" aria-live="polite">
          <span className="puzzle-success-mark">✦</span>
          <strong>{successMessage}</strong>
          <span>Next encounter loading</span>
        </div>
      )}
    </section>
  );
}

function AnalysisPage({ initialGameId = "" }) {
  const [pgn, setPgn] = useState("");
  const [history, setHistory] = useState([]);
  const [selectedGameId, setSelectedGameId] = useState("");
  const [historyLoading, setHistoryLoading] = useState(true);
  const [skillLevel, setSkillLevel] = useState(5);
  const [analysis, setAnalysis] = useState(null);
  const [selectedPly, setSelectedPly] = useState(null);
  const [memeMode, setMemeMode] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [chronicleLoading, setChronicleLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    apiFetch("/api/local/games/history?limit=50")
      .then((data) => {
        if (!cancelled) {
          const games = data.games || [];
          setHistory(games);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setHistory([]);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setHistoryLoading(false);
        }
      });
    return () => { cancelled = true; };
  }, []);

  async function selectSavedGame(gameId, records = history) {
    setSelectedGameId(gameId);
    const game = records.find((item) => String(item.id) === gameId);
    setAnalysis(null);
    setError("");
    if (game?.pgn) {
      setPgn(game.pgn);
      if (game.chronicle_updated_at) {
        setChronicleLoading(true);
        try {
          const saved = await apiFetch(`/api/local/games/${game.id}/chronicle`);
          if (saved.report) {
            setAnalysis(saved.report);
            setSelectedPly(saved.report.moves?.[saved.report.moves.length - 1]?.ply || null);
          }
        } catch {
          // A saved match can still be analyzed again if its Chronicle is unavailable.
        } finally {
          setChronicleLoading(false);
        }
      } else if (initialGameId && String(initialGameId) === gameId) {
        void runAnalysis(game.id, game.pgn);
      }
    }
  }

  function chooseSavedGame(event) {
    void selectSavedGame(event.target.value);
  }

  useEffect(() => {
    if (initialGameId && history.length) {
      void selectSavedGame(String(initialGameId), history);
    }
  }, [initialGameId, history.length]);

  async function runAnalysis(gameId, gamePgn) {
    setError("");
    setAnalysis(null);
    setAnalyzing(true);
    try {
      const result = await apiFetch("/api/analysis", {
        method: "POST",
        body: JSON.stringify({
          ...(gameId ? { game_id: Number(gameId) } : { pgn: gamePgn }),
          skill_level: Number(skillLevel),
          analysis_time: 0.25,
          max_plies: 120
        })
      });
      setAnalysis(result);
      setSelectedPly(result.moves.length ? result.moves[result.moves.length - 1].ply : null);
    } catch (err) {
      setError(err.message);
    } finally {
      setAnalyzing(false);
    }
  }

  async function analyzeGame(event) {
    event.preventDefault();
    await runAnalysis(selectedGameId ? Number(selectedGameId) : null, pgn);
  }

  const currentMove = analysis?.moves.find((move) => move.ply === selectedPly)
    || analysis?.summary?.turning_point
    || analysis?.moves?.[analysis.moves.length - 1];
  const previewBoard = currentMove ? new Chess(currentMove.fen_before).board() : null;

  return (
    <section className="page tool-layout analysis-page">
      <h1>{analysis ? "Match Chronicle" : "Analysis"}</h1>
      <form className="tool-panel analysis-input" onSubmit={analyzeGame}>
        <div className="analysis-input-heading">
          <div>
            <h3>Choose a game to remember</h3>
            <p>Saved matches become private Chronicles with factual Stockfish evidence.</p>
          </div>
          <label>
            Engine strength
            <select value={skillLevel} onChange={(event) => setSkillLevel(event.target.value)}>
              <option value="1">Easy</option>
              <option value="5">Normal</option>
              <option value="10">Hard</option>
              <option value="20">Boss</option>
            </select>
          </label>
        </div>
        <label className="analysis-source-select">
          Saved match
          <select value={selectedGameId} onChange={chooseSavedGame}>
            <option value="">Choose a completed game from match history</option>
            {history.map((game) => (
              <option value={game.id} key={game.id} disabled={!game.pgn}>
                {game.player_result} vs {game.opponent_display || "Opponent"} · {game.total_moves || 0} moves{game.pgn ? "" : " · no PGN"}
              </option>
            ))}
          </select>
          {historyLoading && <span className="analysis-help">Loading saved matches...</span>}
          {chronicleLoading && <span className="analysis-help">Loading saved Chronicle...</span>}
          {!historyLoading && !history.length && <span className="analysis-help">Completed matches will appear here.</span>}
        </label>
        <textarea value={pgn} onChange={(event) => { setPgn(event.target.value); setSelectedGameId(""); setAnalysis(null); }} placeholder="Paste PGN here" />
        <div className="analysis-input-actions">
          <button className="primary-action" type="submit" disabled={analyzing}>{analyzing ? "Analyzing..." : "Analyze game"}</button>
          <button type="button" onClick={() => { setPgn(""); setSelectedGameId(""); setAnalysis(null); setError(""); }}>Clear PGN</button>
          {analyzing && <span className="analysis-progress">Stockfish is reading the position...</span>}
        </div>
        {error && <p className="form-error">{error}</p>}
      </form>

      {!analysis && !analyzing && !error && (
        <article className="tool-panel analysis-empty">
          <h3>Awaiting a game</h3>
          <p>Paste a real PGN above to generate the post-game report.</p>
        </article>
      )}

      {analysis && (
        <div className="analysis-report">
          {analysis.truncated && <p className="analysis-notice">This report analyzes the first 120 plies.</p>}
          <article className="analysis-verdict">
            <div>
              <span className="analysis-eyebrow">Match verdict</span>
              <h2>{analysis.summary.verdict}</h2>
              <p>{analysis.game_info.white} vs {analysis.game_info.black} · {analysis.game_info.result || "unfinished"}</p>
            </div>
            <div className="analysis-result-mark">{analysis.game_info.result || "*"}</div>
          </article>
          <p className="chronicle-status">
            {analysis.game_info.source === "saved_game"
              ? (analysis.chronicle_saved ? "Private Chronicle saved with this match." : "Private saved match.")
              : "Imported PGN · this report is not attached to match history."}
            {analysis.engine && ` · ${analysis.engine.name} strength ${analysis.engine.skill_level}`}
          </p>

          {analysis.reflection && (analysis.reflection.intention || analysis.reflection.feeling || analysis.reflection.note) && (
            <article className="tool-panel chronicle-reflection">
              <div className="analysis-section-heading"><h3>Your reflection</h3><span>Player-authored</span></div>
              {analysis.reflection.intention && <p><strong>Intention:</strong> {MATCH_INTENTIONS.find((item) => item.value === analysis.reflection.intention)?.label || analysis.reflection.intention}</p>}
              {analysis.reflection.feeling && <p><strong>After the game:</strong> {MATCH_REFLECTIONS.find((item) => item.value === analysis.reflection.feeling)?.label || analysis.reflection.feeling}</p>}
              {analysis.reflection.note && <p><strong>Note:</strong> {analysis.reflection.note}</p>}
            </article>
          )}

          <div className="analysis-stat-grid">
            <AnalysisStat label="White accuracy" value={`${analysis.summary.accuracy_white}%`} />
            <AnalysisStat label="Black accuracy" value={`${analysis.summary.accuracy_black}%`} />
            <AnalysisStat label="Blunders" value={analysis.summary.white_blunders + analysis.summary.black_blunders} />
            <AnalysisStat label="Mistakes" value={analysis.summary.white_mistakes + analysis.summary.black_mistakes} />
            <AnalysisStat label="Chaos meter" value={`${analysis.summary.chaos_meter}%`} />
            <AnalysisStat label="Game length" value={`${analysis.summary.total_moves} ply`} />
          </div>

          <article className="tool-panel analysis-pulse">
            <div className="analysis-section-heading">
              <div><span className="analysis-eyebrow">Where the game moved</span><h3>Game pulse</h3></div>
              <span className="analysis-help">Positive is better for White</span>
            </div>
            <div className="pulse-track">
              {analysis.evaluation_timeline.map((point) => (
                <button
                  key={point.ply}
                  type="button"
                  className={`pulse-point pulse-${point.classification}`}
                  title={`Ply ${point.ply}: ${point.display}`}
                  onClick={() => setSelectedPly(point.ply)}
                  style={{ height: `${Math.max(12, Math.min(100, 25 + Math.abs(point.eval_after) * 13))}%` }}
                />
              ))}
            </div>
            <div className="pulse-axis"><span>Opening</span><span>Middlegame</span><span>Endgame</span></div>
          </article>

          <PressureMap timeline={analysis.evaluation_timeline} moments={analysis.pressure_moments || []} />

          <div className="analysis-two-column">
            <article className="tool-panel">
              <div className="analysis-section-heading"><h3>Critical moments</h3><span>{analysis.critical_moments.length}</span></div>
              {analysis.critical_moments.length ? analysis.critical_moments.map((move, index) => (
                <button className="critical-row" type="button" key={move.ply} onClick={() => setSelectedPly(move.ply)}>
                  <strong>#{index + 1} · {move.color} {move.move_number}</strong>
                  <span>{move.played_move_san} → {move.best_move_san}</span>
                  <small>{move.classification} · loss {move.eval_loss.toFixed(2)}</small>
                </button>
              )) : <p>No critical moments crossed the report threshold.</p>}
            </article>

            <article className="tool-panel analysis-preview">
              <div className="analysis-section-heading"><h3>Position preview</h3><span>{currentMove ? `Ply ${currentMove.ply}` : "-"}</span></div>
              {previewBoard && <ChessBoard board={previewBoard} selected={null} premove={null} legalTargets={new Set()} onSquare={() => {}} />}
              {currentMove && <div className="position-details"><strong>{currentMove.played_move_san} <span>vs</span> {currentMove.best_move_san}</strong><p>{currentMove.commentary}</p><small>{currentMove.eval_before_display} → {currentMove.eval_after_display}</small></div>}
            </article>
          </div>

          {currentMove && <TryMomentPanel move={currentMove} skillLevel={skillLevel} />}

          <div className="analysis-two-column">
            <AnalysisMoveCard title="Best move" move={analysis.summary.best_move} />
            <AnalysisMoveCard title="Worst move" move={analysis.summary.worst_move} danger />
          </div>

          <article className="tool-panel blunder-reel">
            <div className="analysis-section-heading">
              <div><span className="analysis-eyebrow">The evidence locker</span><h3>Blunder reel</h3></div>
              <button type="button" className="mode-toggle" onClick={() => setMemeMode((value) => !value)}>{memeMode ? "Meme mode" : "Serious mode"}</button>
            </div>
            {analysis.moves.filter((move) => ["mistake", "blunder", "critical"].includes(move.classification)).length ? (
              analysis.moves.filter((move) => ["mistake", "blunder", "critical"].includes(move.classification)).map((move) => (
                <div className={`reel-row reel-${move.classification}`} key={move.ply}>
                  <strong>Move {move.move_number} {move.color}</strong>
                  <span>{memeMode ? memeComment(move) : `${move.classification[0].toUpperCase() + move.classification.slice(1)}. ${move.commentary}`}</span>
                </div>
              ))
            ) : <p>No mistakes or blunders were detected at the current engine setting.</p>}
          </article>

          <div className="analysis-two-column">
            <article className="tool-panel">
              <h3>Player diagnosis</h3>
              <p className="diagnosis-text">{analysis.summary.player_diagnosis}</p>
            </article>
            <article className="tool-panel">
              <h3>Practice prescription</h3>
              <ul className="practice-list">
                {analysis.summary.practice_recommendations.map((item) => <li key={item}>{item}</li>)}
              </ul>
            </article>
          </div>
        </div>
      )}
    </section>
  );
}

function PressureMap({ timeline = [], moments = [] }) {
  const points = timeline.filter((point) => Number.isFinite(point.time_left));
  if (!points.length) {
    return (
      <article className="tool-panel pressure-map">
        <div className="analysis-section-heading"><h3>Pressure map</h3><span>Clock evidence</span></div>
        <p className="pressure-no-data">Clock data will appear for games recorded with Chess V2 clocks.</p>
      </article>
    );
  }
  const maxTime = Math.max(1, ...points.map((point) => point.time_left));
  return (
    <article className="tool-panel pressure-map">
      <div className="analysis-section-heading">
        <div><span className="analysis-eyebrow">Recorded time remaining</span><h3>Pressure map</h3></div>
        <span>{moments.length} pressure moment{moments.length === 1 ? "" : "s"}</span>
      </div>
      <div className="pressure-track">
        {points.map((point) => (
          <span
            className={`pressure-point pressure-${point.classification}`}
            key={point.ply}
            title={`Ply ${point.ply} · ${formatClock(point.time_left)} left · ${point.classification}`}
            style={{ height: `${Math.max(10, (point.time_left / maxTime) * 100)}%` }}
          />
        ))}
      </div>
      <div className="pressure-moments">
        {moments.length ? moments.map((moment) => (
          <span key={moment.ply}>Ply {moment.ply}: {formatClock(moment.time_left)} left · {moment.classification}</span>
        )) : <span>No move was recorded below the pressure threshold.</span>}
      </div>
    </article>
  );
}

function TryMomentPanel({ move, skillLevel }) {
  const [tryGame, setTryGame] = useState(null);
  const [selected, setSelected] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!move?.fen_before) {
      setTryGame(null);
      return;
    }
    try {
      setTryGame(new Chess(move.fen_before));
      setSelected(null);
      setResult(null);
      setError("");
    } catch {
      setTryGame(null);
      setError("This moment could not be replayed.");
    }
  }, [move?.ply, move?.fen_before]);

  function squareName(row, col) {
    return "abcdefgh"[col] + (8 - row);
  }

  async function compareMove(game, played) {
    setLoading(true);
    setError("");
    try {
      const comparison = await apiFetch("/api/analysis/try-moment", {
        method: "POST",
        body: JSON.stringify({
          fen: move.fen_before,
          move_uci: `${played.from}${played.to}${played.promotion || ""}`,
          skill_level: Number(skillLevel),
          analysis_time: 0.25
        })
      });
      setResult(comparison);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function handleSquare(row, col) {
    if (!tryGame || loading) {
      return;
    }
    const square = squareName(row, col);
    const piece = tryGame.get(square);
    if (!selected) {
      if (piece && piece.color === tryGame.turn()) {
        setSelected(square);
      }
      return;
    }
    if (selected === square) {
      setSelected(null);
      return;
    }
    if (piece && piece.color === tryGame.turn()) {
      setSelected(square);
      return;
    }
    const nextGame = new Chess(tryGame.fen());
    let played;
    try {
      played = nextGame.move({ from: selected, to: square, promotion: "q" });
    } catch {
      played = null;
    }
    if (!played) {
      setSelected(null);
      return;
    }
    setTryGame(nextGame);
    setSelected(null);
    void compareMove(tryGame, played);
  }

  function resetMoment() {
    if (!move?.fen_before) {
      return;
    }
    setTryGame(new Chess(move.fen_before));
    setSelected(null);
    setResult(null);
    setError("");
  }

  const legalTargets = new Set(
    selected && tryGame
      ? tryGame.moves({ verbose: true }).filter((candidate) => candidate.from === selected).map((candidate) => candidate.to)
      : []
  );

  return (
    <article className="tool-panel try-moment">
      <div className="analysis-section-heading">
        <div><span className="analysis-eyebrow">Interactive replay</span><h3>Try the moment</h3></div>
        <span>{move ? `Ply ${move.ply}` : "-"}</span>
      </div>
      <p>Play a legal move from this position. Stockfish will compare it with the preferred move.</p>
      {tryGame && (
        <ChessBoard
          board={tryGame.board()}
          selected={selected}
          premove={null}
          legalTargets={legalTargets}
          onSquare={handleSquare}
          onClearSelection={() => setSelected(null)}
        />
      )}
      <div className="try-moment-actions">
        <button type="button" onClick={resetMoment} disabled={loading}>Reset position</button>
        {loading && <span className="analysis-progress">Comparing your move...</span>}
      </div>
      {error && <p className="form-error">{error}</p>}
      {result && (
        <div className={`try-result ${["best", "good"].includes(result.classification) ? "try-result-good" : "try-result-danger"}`}>
          <strong>{result.played_move_san} · {result.classification}</strong>
          <span>Stockfish preferred {result.best_move_san}.</span>
          <span>{result.eval_before_display} → {result.eval_after_display} · evaluation loss {result.eval_loss.toFixed(2)}</span>
          <p>{result.commentary}</p>
        </div>
      )}
    </article>
  );
}

function AnalysisStat({ label, value }) {
  return <div className="analysis-stat"><strong>{value}</strong><span>{label}</span></div>;
}

function AnalysisMoveCard({ title, move, danger = false }) {
  return (
    <article className={`tool-panel move-card ${danger ? "move-card-danger" : ""}`}>
      <span className="analysis-eyebrow">{title}</span>
      <h3>{move?.played_move_san || "-"}</h3>
      <p>Engine line: {move?.best_move_san || "-"}</p>
      <small>{move?.commentary || "No move data."}</small>
    </article>
  );
}

function memeComment(move) {
  if (move.classification === "critical") return "The position has entered witness protection.";
  if (move.played_move_san.startsWith("Q")) return "The queen has filed a missing person report.";
  if (move.eval_loss >= 3) return "Stockfish stared at this move in silence.";
  return "You had one job.";
}

function ProfilePage({ localStats, onRefresh, onOpenAnalysis }) {
  const identity = localStats?.profile || { id: 1, username: "Player" };
  const [players, setPlayers] = useState([]);
  const [history, setHistory] = useState([]);
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

  async function loadHistory() {
    try {
      const data = await apiFetch("/api/local/games/history?limit=50");
      setHistory(data.games || []);
    } catch (error) {
      setMessage(error.message);
    }
  }

  useEffect(() => {
    setUsername(identity.username || "");
  }, [identity.id, identity.username]);

  useEffect(() => {
    loadPlayers();
    loadHistory();
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

  const games = history.length ? history : (localStats?.recent_games || []);
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
          <h3>Match history</h3>
          {games.length ? games.map((game) => (
            <div className="activity-row" key={game.id}>
              <strong className={`result-${game.player_result}`}>{game.player_result}</strong>
              <span>vs {game.opponent_display || "Opponent"} · {game.total_moves || 0} moves</span>
              <small>
                {game.result_reason || game.mode || "game"} · {game.date || "recently"}
                {game.pgn ? " · ready for analysis" : ""}
                {game.chronicle_updated_at ? " · Chronicle ready" : ""}
                {game.reflection_feeling ? ` · ${MATCH_REFLECTIONS.find((item) => item.value === game.reflection_feeling)?.label || game.reflection_feeling}` : ""}
              </small>
              {game.pgn && <button className="history-action" type="button" onClick={() => onOpenAnalysis?.(game.id)}>Open Chronicle</button>}
            </div>
          )) : <p>No completed games yet.</p>}
        </div>
        <div className="profile-card profile-activity-card">
          <h3>Recent puzzle attempts</h3>
          {puzzles.length ? puzzles.map((attempt) => (
            <div className="activity-row" key={attempt.id}>
              <strong className={attempt.solved ? "result-win" : "result-loss"}>{attempt.solved ? "Solved" : "Failed"}</strong>
              <span>Training encounter · {attempt.attempts} attempt{attempt.attempts === 1 ? "" : "s"}</span>
              <small>{attempt.puzzle_rating || "Unrated"} · {puzzleThemeLabels({ themes: attempt.themes }).join(", ") || "Tactical"}</small>
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
