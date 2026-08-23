import { fen_to_board, get_legal_moves, make_move } from "./chessEngine";

export class PuzzleManager {
  constructor(puzzles = []) {
    this.puzzles = puzzles;
    this.current_puzzle = null;
    this.current_step = 0;
    this.game = null;
    this.attempts = 0;
  }

  start_puzzle(puzzle_id) {
    this.current_puzzle = this.puzzles.find((puzzle) => puzzle.id === puzzle_id) || this.puzzles[0];
    if (!this.current_puzzle) {
      this.game = null;
      return null;
    }
    this.current_step = 0;
    this.attempts = 0;
    this.game = fen_to_board(this.current_puzzle.solver_fen);
    return this.current_puzzle;
  }

  legal_moves() {
    return this.game ? get_legal_moves(this.game, this.game.turn()) : [];
  }

  check_move(move) {
    if (!this.current_puzzle || !this.game || this.is_complete()) {
      return { ok: false, complete: false, san: "", expected: "" };
    }
    this.attempts += 1;
    const expected = this.current_puzzle.solution_moves[this.current_step];
    const testGame = fen_to_board(this.game.fen());
    let played = null;
    try {
      played = make_move(testGame, move);
    } catch {
      played = null;
    }
    const playedUci = played ? `${played.from}${played.to}${played.promotion || ""}` : "";
    if (!played || playedUci !== expected) {
      return { ok: false, complete: false, san: played?.san || "", expected };
    }

    make_move(this.game, move);
    this.current_step += 1;
    return {
      ok: true,
      complete: this.is_complete(),
      san: played.san,
      uci: playedUci,
      expected
    };
  }

  play_forced_reply() {
    if (!this.current_puzzle || !this.game || this.is_complete()) {
      return null;
    }
    const expected = this.current_puzzle.solution_moves[this.current_step];
    const move = this.legal_moves().find((legalMove) => {
      const uci = `${legalMove.from}${legalMove.to}${legalMove.promotion || ""}`;
      return uci === expected;
    });
    if (!move) {
      return null;
    }
    const played = make_move(this.game, move);
    this.current_step += 1;
    return played;
  }

  is_complete() {
    return Boolean(this.current_puzzle && this.current_step >= this.current_puzzle.solution_moves.length);
  }

  hint() {
    return this.current_puzzle?.solution_moves[this.current_step] || null;
  }
}

export async function loadPuzzles(path = "/assets/puzzles/puzzles.json") {
  const response = await fetch(path);
  if (!response.ok) {
    throw new Error("Could not load puzzles");
  }
  const puzzles = await response.json();
  return puzzles.filter((puzzle) => puzzle.solver_fen && Array.isArray(puzzle.solution_moves));
}
