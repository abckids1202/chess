import {
  PIECE_VALUE,
  develops_piece,
  evaluate_board,
  get_piece_at,
  get_legal_moves,
  is_castling,
  is_promotion,
  make_move_copy,
  move_gives_check,
  move_gives_checkmate,
  opposite
} from "./chessEngine";

function randomChoice(items) {
  return items[Math.floor(Math.random() * items.length)];
}

export function randomBot(_board, legalMoves) {
  return randomChoice(legalMoves);
}

export function captureBot(board, legalMoves) {
  let bestMove = null;
  let bestValue = -999;

  for (const move of legalMoves) {
    const captured = get_piece_at(board, move.to);
    if (!captured) {
      continue;
    }
    const value = PIECE_VALUE[captured.type] || 0;
    if (value > bestValue) {
      bestValue = value;
      bestMove = move;
    }
  }

  return bestMove || randomChoice(legalMoves);
}

export function priorityBot(board, legalMoves, _color, personality = "machine") {
  const weights = BOT_PERSONALITIES[personality] || BOT_PERSONALITIES.machine;
  const scoredMoves = legalMoves.map((move) => {
    let score = Math.random() * 0.01;

    if (move_gives_checkmate(board, move)) {
      score += 10000;
    }

    const captured = get_piece_at(board, move.to);
    if (captured) {
      score += (PIECE_VALUE[captured.type] || 0) * 100 * weights.capture;
    }

    if (move_gives_check(board, move)) {
      score += 50 * weights.check;
    }

    if (is_promotion(move)) {
      score += 800;
    }

    if (is_castling(move)) {
      score += 60 * weights.castle;
    }

    if (develops_piece(move)) {
      score += 20 * weights.develop;
    }

    return { move, score };
  });

  scoredMoves.sort((a, b) => b.score - a.score);
  return scoredMoves[0]?.move || randomChoice(legalMoves);
}

export function onePlyBot(board, legalMoves, color) {
  let bestMove = null;
  let bestScore = -999999;

  for (const move of legalMoves) {
    const nextBoard = make_move_copy(board, move);
    const score = evaluate_board(nextBoard, color);
    if (score > bestScore) {
      bestScore = score;
      bestMove = move;
    }
  }

  return bestMove || randomChoice(legalMoves);
}

export function twoPlyBot(board, legalMoves, color) {
  let bestMove = null;
  let bestScore = -999999;

  for (const move of legalMoves) {
    const boardAfterMove = make_move_copy(board, move);
    const opponent = opposite(color);
    const opponentMoves = get_legal_moves(boardAfterMove, opponent);

    if (!opponentMoves.length) {
      const score = evaluate_board(boardAfterMove, color);
      if (score > bestScore) {
        bestScore = score;
        bestMove = move;
      }
      continue;
    }

    let worstScore = 999999;
    for (const reply of opponentMoves) {
      const boardAfterReply = make_move_copy(boardAfterMove, reply);
      const score = evaluate_board(boardAfterReply, color);
      if (score < worstScore) {
        worstScore = score;
      }
    }

    if (worstScore > bestScore) {
      bestScore = worstScore;
      bestMove = move;
    }
  }

  return bestMove || randomChoice(legalMoves);
}

export const BOT_LEVELS = {
  1: { depth: 0, randomness: 0.8 },
  2: { depth: 0, randomness: 0.5 },
  3: { depth: 1, randomness: 0.3 },
  4: { depth: 1, randomness: 0.15 },
  5: { depth: 2, randomness: 0.1 },
  6: { depth: 2, randomness: 0.05 },
  7: { depth: 2, randomness: 0.03 }
};

export const STOCKFISH_LEVELS = [
  { value: 1, label: "Stockfish Easy" },
  { value: 5, label: "Stockfish Normal" },
  { value: 10, label: "Stockfish Hard" },
  { value: 20, label: "Stockfish Boss" }
];

export const BOT_PERSONALITIES = {
  gambler: { label: "The Gambler", capture: 1.4, check: 1.3, castle: 0.4, develop: 0.8 },
  coward: { label: "The Coward", capture: 0.8, check: 0.7, castle: 1.5, develop: 1.2 },
  hunter: { label: "The Hunter", capture: 2.2, check: 1.5, castle: 0.7, develop: 1 },
  collector: { label: "The Collector", capture: 2.8, check: 0.8, castle: 0.6, develop: 0.8 },
  trickster: { label: "The Trickster", capture: 1.2, check: 2.2, castle: 0.8, develop: 1.3 },
  monk: { label: "The Endgame Monk", capture: 1.1, check: 0.9, castle: 1.2, develop: 1.8 },
  machine: { label: "The Machine", capture: 1.5, check: 1.4, castle: 1.1, develop: 1.2 }
};

export class ChessBot {
  constructor(name, level = 1, personality = "machine") {
    this.name = name;
    this.level = level;
    this.personality = personality;
  }

  choose_move(_board, legalMoves) {
    return randomChoice(legalMoves);
  }

  choose_with_randomness(bestMove, legalMoves) {
    const settings = BOT_LEVELS[this.level] || BOT_LEVELS[1];
    if (Math.random() < settings.randomness) {
      return randomChoice(legalMoves);
    }
    return bestMove || randomChoice(legalMoves);
  }
}

export class RandomBot extends ChessBot {
  choose_move(board, legalMoves, color) {
    return randomBot(board, legalMoves, color);
  }
}

export class GreedyBot extends ChessBot {
  choose_move(board, legalMoves, color) {
    const bestMove = captureBot(board, legalMoves, color);
    return this.choose_with_randomness(bestMove, legalMoves);
  }
}

export class PriorityBot extends ChessBot {
  choose_move(board, legalMoves, color) {
    const bestMove = priorityBot(board, legalMoves, color, this.personality);
    return this.choose_with_randomness(bestMove, legalMoves);
  }
}

export class EvaluationBot extends ChessBot {
  choose_move(board, legalMoves, color) {
    const settings = BOT_LEVELS[this.level] || BOT_LEVELS[1];
    const bestMove = settings.depth >= 2
      ? twoPlyBot(board, legalMoves, color)
      : onePlyBot(board, legalMoves, color);
    return this.choose_with_randomness(bestMove, legalMoves);
  }
}

export class StockfishBot extends ChessBot {
  constructor(name, level = 5, apiTarget = "") {
    super(name, level, "machine");
    this.apiTarget = apiTarget;
  }

  async choose_move(board) {
    const response = await fetch(`${this.apiTarget}/api/bot/stockfish/move`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        fen: board.fen(),
        skill_level: this.level,
        move_time: 0.35
      })
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.detail || "Stockfish could not choose a move");
    }
    return {
      from: data.move.slice(0, 2),
      to: data.move.slice(2, 4),
      ...(data.move.length > 4 ? { promotion: data.move[4] } : {})
    };
  }
}

export const BOT_DEFINITIONS = {
  random: {
    label: "Random Bot",
    description: "Chooses any legal move. Great for testing.",
    create: (level, personality) => new RandomBot("Random Bot", level, personality)
  },
  capture: {
    label: "Capture Bot",
    description: "Captures the most valuable available piece.",
    create: (level, personality) => new GreedyBot("Capture Bot", level, personality)
  },
  priority: {
    label: "Priority Bot",
    description: "Checks for mates, captures, checks, promotions, castling, and development.",
    create: (level, personality) => new PriorityBot("Priority Bot", level, personality)
  },
  onePly: {
    label: "One-Move Evaluation Bot",
    description: "Tries every legal move and keeps the best resulting board.",
    create: (level, personality) => new EvaluationBot("One-Move Evaluation Bot", Math.max(level, 3), personality)
  },
  twoPly: {
    label: "Two-Ply Bot",
    description: "Looks at the opponent's best reply before choosing.",
    create: (level, personality) => new EvaluationBot("Two-Ply Bot", Math.max(level, 5), personality)
  },
  stockfish: {
    label: "Stockfish",
    description: "A real chess engine connected through the FastAPI backend.",
    create: (level) => new StockfishBot("Stockfish", Math.max(level, 1), import.meta.env.VITE_API_TARGET || "")
  }
};
