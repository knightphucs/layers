/**
 * LAYERS — Chat Types
 * ==========================================
 * Type definitions for the chat system.
 * Mirrors backend/app/schemas/chat.py.
 *
 * PATTERN: Same as types/inbox.ts and types/connections.ts.
 */

import { User } from "./index";

// ============================================================
// ENUMS
// ============================================================

export type ChatRoomType = "DIRECT" | "CAMPFIRE";
export type ChatRoomStatus = "ACTIVE" | "CLOSED";

// ============================================================
// CORE MODELS (mirror backend responses)
// ============================================================

export interface ChatMessage {
  id: string;
  room_id: string;
  sender_id: string;
  content: string;
  created_at: string;
}

export interface ChatRoom {
  id: string;
  room_type: ChatRoomType;
  status: ChatRoomStatus;
  user_a_id: string | null;
  user_b_id: string | null;
  message_count: number;
  last_activity_at: string;
  created_at: string;
}

export interface ChatRoomDetail extends ChatRoom {
  recent_messages: ChatMessage[];
  other_user_id: string | null;
}

// ============================================================
// LIST RESPONSE (paginated messages)
// ============================================================

export interface MessageListResponse {
  items: ChatMessage[];
  has_more: boolean;
  next_cursor: string | null; // ISO datetime
}

// ============================================================
// REQUESTS
// ============================================================

export interface DirectRoomCreateRequest {
  other_user_id: string;
}

export interface SendMessageRequest {
  content: string;
}

// ============================================================
// CLIENT-SIDE EXTENDED MODELS
// ============================================================

/** A message that includes optimistic-send state for the UI. */
export interface ChatMessageWithStatus extends ChatMessage {
  /** "sending" → POST in flight; "sent" → server confirmed; "failed" → retry needed. */
  status?: "sending" | "sent" | "failed";
  /** Local-only id for optimistic messages (replaced when server returns canonical id). */
  client_id?: string;
}

/** Room with the other user's profile attached (denormalized for list view). */
export interface ChatRoomItem extends ChatRoom {
  other_user_id: string | null;
  other_user?: Pick<User, "id" | "username" | "avatar_url"> | null;
  last_message_preview?: string | null;
}

// ============================================================
// WEBSOCKET PROTOCOL
// ============================================================

// Client → Server
export type WSClientMessage =
  | { type: "message"; content: string }
  | { type: "ping" };

// Server → Client (discriminated by `type`)
export type WSServerMessage =
  | { type: "message"; data: ChatMessage }
  | { type: "presence"; event: "join" | "leave"; user_id: string }
  | { type: "error"; code: string; message: string }
  | { type: "pong" };

/** Connection state tracked by the WebSocketClient. */
export type WSConnectionState =
  | "idle" // never connected
  | "connecting"
  | "connected"
  | "reconnecting"
  | "closed";

// ============================================================
// CLOSE CODES (mirror backend WSCloseCode)
// ============================================================

export const WS_CLOSE_CODES = {
  UNAUTHORIZED: 4001,
  FORBIDDEN: 4003,
  ROOM_NOT_FOUND: 4004,
  ROOM_CLOSED: 4005,
  INVALID_PAYLOAD: 4400,
  INTERNAL: 4500,
} as const;
