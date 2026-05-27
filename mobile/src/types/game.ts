/**
 * LAYERS — Campfire Game Types
 * ============================================
 * Mirrors backend/app/schemas/game.py.
 */

// ============================================================
// ENUMS
// ============================================================

export type GameState = "WAITING" | "COMPLETED";
export type RoundState = "ANSWERING" | "VOTING" | "REVEALED";

// ============================================================
// CORE MODELS
// ============================================================

export interface GameAnswer {
  id: string;
  round_id: string;
  /** Hidden (null) during ANSWERING/VOTING. Filled when REVEALED. */
  user_id: string | null;
  content: string;
  vote_count: number;
  is_mine: boolean;
  username: string | null;
  avatar_url: string | null;
}

export interface GameRound {
  id: string;
  round_number: number;
  question_text: string;
  state: RoundState;
  answers: GameAnswer[];
  winner_user_id: string | null;
  winning_answer_id: string | null;
  winner_username: string | null;
  winner_avatar_url: string | null;
  created_at: string;
  revealed_at: string | null;
}

export interface Game {
  id: string;
  room_id: string;
  starter_id: string;
  state: GameState;
  round_count: number;
  current_round: GameRound | null;
  created_at: string;
  ended_at: string | null;
  my_answer_submitted: boolean;
  my_vote_cast: boolean;
}

// ============================================================
// REQUESTS
// ============================================================

export interface AnswerSubmitRequest {
  content: string;
}

export interface VoteCastRequest {
  answer_id: string;
}

// ============================================================
// WEBSOCKET EVENTS
// ============================================================

export type GameWSEventType =
  | "started"
  | "answer_submitted"
  | "phase_changed"
  | "vote_cast"
  | "round_revealed"
  | "next_round"
  | "ended";

export interface GameWSEvent {
  type: "game_event";
  event: GameWSEventType;
  game_id: string;
  room_id: string;
  actor_user_id?: string | null;
  phase?: string | null;
  round_id?: string | null;
}

// ============================================================
// TYPING INDICATORS (Day 5 chat polish)
// ============================================================

export type WSClientTypingFrame =
  | { type: "typing_start" }
  | { type: "typing_stop" };

export interface WSServerTypingFrame {
  type: "typing";
  event: "start" | "stop";
  user_id: string;
}
