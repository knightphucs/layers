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
  center_latitude: number | null;
  center_longitude: number | null;
  radius_meters: number | null;
  expires_at: string | null;
  name: string | null;
  creator_id: string | null;
  message_count: number;
  last_activity_at: string;
  created_at: string;
}

export interface ChatRoomDetail extends ChatRoom {
  recent_messages: ChatMessage[];
  other_user_id: string | null;
}

// ============================================================
// LIST / RESPONSE (paginated messages)
// ============================================================

export interface MessageListResponse {
  items: ChatMessage[];
  has_more: boolean;
  next_cursor: string | null; // ISO datetime
}
export interface DirectRoomCreateRequest {
  other_user_id: string;
}

export interface SendMessageRequest {
  content: string;
}

export interface CampfireFindOrCreateRequest {
  latitude: number;
  longitude: number;
  name?: string;
}

export interface CampfireJoinRequest {
  latitude: number;
  longitude: number;
}

// ============================================================
// CAMPFIRE RESPONSES
// ============================================================

export interface CampfireMemberInfo {
  user_id: string;
  joined_at: string;
  is_online: boolean;
  username: string | null;
  avatar_url: string | null;
}

export interface CampfireMembersResponse {
  members: CampfireMemberInfo[];
  online_count: number;
  total_count: number;
}

export interface CampfireNearbyItem {
  id: string;
  name: string | null;
  center_latitude: number;
  center_longitude: number;
  radius_meters: number;
  expires_at: string;
  distance_meters: number;
  online_count: number;
  creator_id: string | null;
  created_at: string;
}

export interface CampfireNearbyResponse {
  items: CampfireNearbyItem[];
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
