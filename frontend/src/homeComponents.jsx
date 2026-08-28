import React, { useEffect, useRef, useState } from "react";

const NAV_GROUPS = [
  { label: "Play", items: ["Play", "Bot Battle", "Puzzle"] },
  { label: "Review", items: ["Analysis", "Profile"] },
  { label: "Community", items: ["Leaderboard"] }
];

const PREVIEW_BOARD = [
  ["bR", "bN", "bB", "bQ", "bK", "bB", "bN", "bR"],
  ["bP", "bP", "bP", "bP", "bP", "bP", "bP", "bP"],
  ["--", "--", "--", "--", "--", "--", "--", "--"],
  ["--", "--", "--", "--", "--", "--", "--", "--"],
  ["--", "--", "--", "--", "--", "--", "--", "--"],
  ["--", "--", "--", "--", "--", "--", "--", "--"],
  ["wP", "wP", "wP", "wP", "wP", "wP", "wP", "wP"],
  ["wR", "wN", "wB", "wQ", "wK", "wB", "wN", "wR"]
];

const RESULT_LABELS = {
  win: "Win",
  loss: "Loss",
  draw: "Draw",
  unfinished: "In progress"
};

function formatDate(value) {
  if (!value) {
    return "Recently";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric"
  }).format(parsed);
}

function modeLabel(game) {
  if (game?.mode === "bot") {
    return "Bot battle";
  }
  if (game?.mode === "local_1v1" || game?.mode === "local") {
    return "Local game";
  }
  return game?.mode || "Chess game";
}

export function TopNav({ page, onNavigate, username = "Profile", onOpenCommand }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const updateScrollState = () => setScrolled(window.scrollY > 12);
    updateScrollState();
    window.addEventListener("scroll", updateScrollState, { passive: true });
    return () => window.removeEventListener("scroll", updateScrollState);
  }, []);

  function navigate(nextPage) {
    onNavigate(nextPage);
    setMenuOpen(false);
  }

  return (
    <nav className={`top-nav${scrolled ? " scrolled" : ""}`} aria-label="Primary navigation">
      <button className="brand" type="button" onClick={() => navigate("Home")}>
        CHESS V2
      </button>
      <div className="nav-groups">
        {NAV_GROUPS.map((group) => (
          <div className="nav-group" key={group.label}>
            <span className="nav-group-label">{group.label}</span>
            <div className="nav-group-links">
              {group.items.map((item) => (
                <button
                  className={`${page === item ? "active " : ""}${item === "Play" ? "nav-play" : ""}`}
                  type="button"
                  key={item}
                  onClick={() => navigate(item)}
                  aria-current={page === item ? "page" : undefined}
                >
                  {item}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>
      <button className="nav-search" type="button" onClick={onOpenCommand}>
        <span aria-hidden="true">⌕</span>
        Search
      </button>
      <button className="mobile-play-button" type="button" onClick={() => navigate("Play")}>
        Play
      </button>
      <button
        className="mobile-menu-toggle"
        type="button"
        aria-expanded={menuOpen}
        aria-controls="mobile-navigation"
        onClick={() => setMenuOpen((open) => !open)}
      >
        {menuOpen ? "Close" : "Menu"}
      </button>
      <button className="login-button" type="button" onClick={() => navigate("Profile")}>
        {username || "Profile"}
      </button>
      {menuOpen && (
        <div className="mobile-nav-panel" id="mobile-navigation">
          <button className="mobile-search-button" type="button" onClick={() => { onOpenCommand?.(); setMenuOpen(false); }}>
            Search pages
          </button>
          {NAV_GROUPS.map((group) => (
            <div className="mobile-nav-group" key={group.label}>
              <span className="nav-group-label">{group.label}</span>
              {group.items.map((item) => (
                <button
                  className={`${page === item ? "active " : ""}${item === "Play" ? "nav-play" : ""}`}
                  type="button"
                  key={item}
                  onClick={() => navigate(item)}
                  aria-current={page === item ? "page" : undefined}
                >
                  {item}
                </button>
              ))}
            </div>
          ))}
        </div>
      )}
    </nav>
  );
}

export function HomePage({
  apiFetch,
  localStats,
  onRefreshStats,
  onPlay,
  onProfile,
  onNavigate,
  onOpenAnalysis
}) {
  const [recentGames, setRecentGames] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [historyError, setHistoryError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setHistoryLoading(true);
    setHistoryError(false);
    onRefreshStats?.();
    apiFetch("/api/local/games/history?limit=3")
      .then((data) => {
        if (!cancelled) {
          setRecentGames(data.games || []);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setRecentGames([]);
          setHistoryError(true);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setHistoryLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [apiFetch]);

  const latestGame = recentGames[0];
  const latestChronicle = recentGames.find((game) => game.chronicle_updated_at);
  const featuredGame = latestChronicle || latestGame;
  const stats = localStats || {};
  const username = stats.profile?.username;

  return (
    <section className="page home-page" aria-labelledby="home-title">
      <div className="home-hero">
        <div className="hero-copy">
          <p className="eyebrow">cosmic chess, now on the web</p>
          <h1 id="home-title">CHESS V2</h1>
          <p className="home-lede">
            Play a game, remember the turning point, and come back to try it another way.
          </p>
          <div className="hero-actions">
            <button className="primary-action" type="button" onClick={onPlay}>
              Play a game
            </button>
            <button className="secondary-action" type="button" onClick={onProfile}>
              View match history
            </button>
          </div>
          <p className="hero-note">
            {username ? `Welcome back, ${username}. Your local chess shelf is ready.` : "Your games and reflections stay on this device."}
          </p>
        </div>
        <ThemePreview />
      </div>

      <div className="home-content">
        <ContinueStory
          game={featuredGame}
          chronicleGame={featuredGame?.chronicle_updated_at ? featuredGame : null}
          loading={historyLoading}
          error={historyError}
          onPlay={onPlay}
          onProfile={onProfile}
          onOpenAnalysis={onOpenAnalysis}
        />
        <QuickPlayGrid onPlay={onPlay} onNavigate={onNavigate} />
        <ProgressStrip stats={stats} />
        <IdentitySection />
      </div>
    </section>
  );
}

function ContinueStory({ game, chronicleGame, loading, error, onPlay, onProfile, onOpenAnalysis }) {
  return (
    <section className="dashboard-panel continue-panel" aria-labelledby="continue-title">
      <div className="home-section-heading">
        <div>
          <p className="section-kicker">Memory shelf</p>
          <h2 id="continue-title">Continue your story</h2>
        </div>
        <button className="text-action" type="button" onClick={onProfile}>View all games</button>
      </div>
      {loading && (
        <div className="story-skeleton" role="status" aria-label="Loading recent game">
          <span className="skeleton-line skeleton-short" />
          <span className="skeleton-line skeleton-long" />
          <span className="skeleton-line skeleton-medium" />
        </div>
      )}
      {!loading && error && (
        <div className="home-empty home-error" role="status">
          <strong>Your games are still safe.</strong>
          <p>The local history shelf is unavailable right now. Open your profile to try again.</p>
          <button className="secondary-action" type="button" onClick={onProfile}>Open profile</button>
        </div>
      )}
      {!loading && !error && !game && (
        <div className="home-empty">
          <div>
            <strong>Your first game is waiting.</strong>
            <p>Start with an intention, play normally, and CHESS V2 will remember the important moment.</p>
          </div>
          <button className="primary-action" type="button" onClick={onPlay}>Start your first game</button>
        </div>
      )}
      {!loading && !error && game && (
        <article className="story-card">
          <div className="story-card-main">
            <div className="story-topline">
              <span className={`result-badge result-${game.player_result || "unfinished"}`}>
                {RESULT_LABELS[game.player_result] || "Saved game"}
              </span>
              <span>{formatDate(game.date)}</span>
            </div>
            <h3>{modeLabel(game)} vs {game.opponent_display || "Opponent"}</h3>
            <p className="story-meta">
              {game.time_control || "10+0"} · {game.total_moves || 0} moves
              {game.result_reason ? ` · ${game.result_reason}` : ""}
            </p>
          </div>
          <div className="story-card-actions">
            {chronicleGame && (
              <button className="primary-action" type="button" onClick={() => onOpenAnalysis(chronicleGame.id)}>
                Open Chronicle
              </button>
            )}
            <button className="secondary-action" type="button" onClick={onProfile}>
              {chronicleGame ? "View history" : "Review game"}
            </button>
          </div>
        </article>
      )}
    </section>
  );
}

function QuickPlayGrid({ onPlay, onNavigate }) {
  const actions = [
    { label: "Local game", detail: "Play someone beside you", action: onPlay },
    { label: "Bot battle", detail: "Choose a sparring partner", action: () => onNavigate("Bot Battle") },
    { label: "Daily puzzle", detail: "Find one forcing move", action: () => onNavigate("Puzzle") },
    { label: "Analyze a game", detail: "Learn from a saved record", action: () => onNavigate("Analysis") }
  ];

  return (
    <section aria-labelledby="quick-play-title">
      <div className="home-section-heading compact-heading">
        <div>
          <p className="section-kicker">Choose your next move</p>
          <h2 id="quick-play-title">Start somewhere</h2>
        </div>
      </div>
      <div className="quick-play-grid">
        {actions.map((item) => (
          <button className="quick-play-card" type="button" key={item.label} onClick={item.action}>
            <strong>{item.label}</strong>
            <span>{item.detail}</span>
          </button>
        ))}
      </div>
    </section>
  );
}

function ProgressStrip({ stats }) {
  const items = [
    ["Games played", stats.games_played],
    ["Wins", stats.wins],
    ["Puzzles solved", stats.puzzles_solved],
    ["Chronicles", stats.chronicles_created]
  ];

  return (
    <section className="dashboard-panel progress-panel" aria-labelledby="progress-title">
      <div className="home-section-heading compact-heading">
        <div>
          <p className="section-kicker">Your recorded rhythm</p>
          <h2 id="progress-title">Small facts, real progress</h2>
        </div>
      </div>
      <div className="progress-strip">
        {items.map(([label, value]) => (
          <div className="progress-item" key={label}>
            <strong>{value ?? "—"}</strong>
            <span>{label}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function IdentitySection() {
  const principles = [
    ["Play with intention", "Choose what you want to practice before the clock starts."],
    ["Remember the turning point", "Your moves, clock, and reflection stay together in one Chronicle."],
    ["Try the moment again", "Replay the position and test the move you almost played." ]
  ];

  return (
    <section className="identity-section" aria-labelledby="identity-title">
      <div className="home-section-heading compact-heading">
        <div>
          <p className="section-kicker">What makes this different</p>
          <h2 id="identity-title">Chess that remembers the moment</h2>
        </div>
      </div>
      <div className="identity-grid">
        {principles.map(([title, detail], index) => (
          <article className="identity-card" key={title}>
            <span className="identity-index">0{index + 1}</span>
            <h3>{title}</h3>
            <p>{detail}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

export function ThemePreview() {
  return (
    <aside className="theme-preview" aria-label="Chess theme preview">
      <div className="mini-board">
        {PREVIEW_BOARD.flatMap((row, rowIndex) => row.map((code, colIndex) => (
          <div
            className={`mini-square ${(rowIndex + colIndex) % 2 === 0 ? "light" : "dark"}`}
            key={`${rowIndex}-${colIndex}`}
          >
            {code !== "--" && (
              <img
                src={`/assets/pieces/${code}.png`}
                alt=""
                aria-hidden="true"
              />
            )}
          </div>
        )))}
      </div>
      <div className="preview-panel">
        <strong>Theme preview</strong>
        <span>Real pieces. Cosmic board. Your next game starts here.</span>
      </div>
    </aside>
  );
}

export function ScrollProgress() {
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const updateProgress = () => {
      const scrollable = document.documentElement.scrollHeight - window.innerHeight;
      setProgress(scrollable > 0 ? Math.min(1, window.scrollY / scrollable) : 0);
    };
    updateProgress();
    window.addEventListener("scroll", updateProgress, { passive: true });
    window.addEventListener("resize", updateProgress);
    return () => {
      window.removeEventListener("scroll", updateProgress);
      window.removeEventListener("resize", updateProgress);
    };
  }, []);

  return (
    <div className="scroll-progress" aria-hidden="true">
      <span style={{ transform: `scaleX(${progress})` }} />
    </div>
  );
}

export function BackToTop() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const updateVisibility = () => setVisible(window.scrollY > 520);
    updateVisibility();
    window.addEventListener("scroll", updateVisibility, { passive: true });
    return () => window.removeEventListener("scroll", updateVisibility);
  }, []);

  if (!visible) {
    return null;
  }

  return (
    <button
      className="back-to-top"
      type="button"
      aria-label="Back to top"
      title="Back to top"
      onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}
    >
      ↑
    </button>
  );
}

const COMMAND_ITEMS = [
  { page: "Play", label: "Play a local game", hint: "Start" },
  { page: "Bot Battle", label: "Bot battle", hint: "Play" },
  { page: "Puzzle", label: "Daily puzzle", hint: "Practice" },
  { page: "Analysis", label: "Analyze a game", hint: "Review" },
  { page: "Profile", label: "Match history and profile", hint: "Review" },
  { page: "Leaderboard", label: "Leaderboard", hint: "Community" },
  { page: "Home", label: "Home dashboard", hint: "Navigate" }
];

export function CommandPalette({ open, onClose, onNavigate }) {
  const [query, setQuery] = useState("");
  const inputRef = useRef(null);

  useEffect(() => {
    if (!open) {
      setQuery("");
      return;
    }
    window.setTimeout(() => inputRef.current?.focus(), 0);
  }, [open]);

  if (!open) {
    return null;
  }

  const normalized = query.trim().toLowerCase();
  const results = COMMAND_ITEMS.filter((item) =>
    `${item.label} ${item.hint}`.toLowerCase().includes(normalized)
  );

  function choose(page) {
    onNavigate(page);
    onClose();
  }

  return (
    <div className="command-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="command-palette"
        role="dialog"
        aria-modal="true"
        aria-labelledby="command-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="command-heading">
          <div>
            <p className="section-kicker">Quick navigation</p>
            <h2 id="command-title">Where next?</h2>
          </div>
          <button className="command-close" type="button" aria-label="Close search" onClick={onClose}>×</button>
        </div>
        <input
          ref={inputRef}
          className="command-input"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Escape") {
              onClose();
            } else if (event.key === "Enter" && results[0]) {
              choose(results[0].page);
            }
          }}
          placeholder="Search pages and actions"
          aria-label="Search pages and actions"
        />
        <div className="command-results" role="listbox" aria-label="Navigation results">
          {results.length ? results.map((item) => (
            <button
              className="command-result"
              type="button"
              role="option"
              key={item.page}
              onClick={() => choose(item.page)}
            >
              <span>
                <strong>{item.label}</strong>
                <small>{item.hint}</small>
              </span>
              <span aria-hidden="true">↵</span>
            </button>
          )) : <p className="command-empty">No pages match that search.</p>}
        </div>
        <p className="command-hint"><kbd>Ctrl</kbd><span>+</span><kbd>K</kbd> to open · <kbd>Esc</kbd> to close</p>
      </section>
    </div>
  );
}
