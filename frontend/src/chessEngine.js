import { Chess } from "chess.js";

export const PIECE_VALUE = {
  p: 1,
  n: 3,
  b: 3,
  r: 5,
  q: 9,
  k: 1000
};

function asGame(board) {
  if (board instanceof Chess) {
    return board;
  }
  return new Chess(board);
}

function cloneGame(board) {
  return new Chess(board_to_fen(board));
}

function fenWithTurn(board, turn) {
  const parts = board_to_fen(board).split(" ");
  parts[1] = turn;
  return parts.join(" ");
}

export function get_legal_moves(board, turn) {
  const game = turn ? new Chess(fenWithTurn(board, turn)) : asGame(board);
  return game.moves({ verbose: true });
}

export function make_move(board, move) {
  return asGame(board).move(move);
}

export function make_move_copy(board, move) {
  const game = cloneGame(board);
  game.move(move);
  return game;
}

export function undo_move(board) {
  return asGame(board).undo();
}

export function is_check(board, color) {
  const game = color ? new Chess(fenWithTurn(board, color)) : asGame(board);
  return game.isCheck();
}

export function is_checkmate(board, color) {
  const game = color ? new Chess(fenWithTurn(board, color)) : asGame(board);
  return game.isCheckmate();
}

export function is_stalemate(board, color) {
  const game = color ? new Chess(fenWithTurn(board, color)) : asGame(board);
  return game.isStalemate();
}

export function opposite(color) {
  return color === "w" ? "b" : "w";
}

export function evaluate_board(board, color = "w") {
  const game = asGame(board);
  const whiteScore = game.board().flat().reduce((score, piece) => {
    if (!piece) {
      return score;
    }
    const value = PIECE_VALUE[piece.type] || 0;
    return score + (piece.color === "w" ? value : -value);
  }, 0);
  return color === "w" ? whiteScore : -whiteScore;
}

export function board_to_fen(board) {
  return asGame(board).fen();
}

export function fen_to_board(fen) {
  return new Chess(fen);
}

export function get_piece_at(board, square) {
  return asGame(board).get(square);
}

export function move_gives_check(board, move) {
  const game = cloneGame(board);
  const played = game.move(move);
  return Boolean(played && game.isCheck());
}

export function move_gives_checkmate(board, move) {
  const game = cloneGame(board);
  const played = game.move(move);
  return Boolean(played && game.isCheckmate());
}

export function is_promotion(move) {
  return Boolean(move.promotion || move.flags?.includes("p"));
}

export function is_castling(move) {
  return move.flags?.includes("k") || move.flags?.includes("q");
}

export function develops_piece(move) {
  if (!["n", "b"].includes(move.piece)) {
    return false;
  }
  return ["1", "8"].includes(move.from[1]) && !["1", "8"].includes(move.to[1]);
}
