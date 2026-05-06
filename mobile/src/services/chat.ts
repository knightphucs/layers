/**
 * LAYERS — Chat Service
 * =====================================
 * REST helpers + WebSocketClient class for real-time chat.
 *
 * PATTERN:
 *   - REST helpers exported as object literal (same as authService, inboxService)
 *   - WebSocketClient is a class because it owns mutable lifecycle state
 *
 * Backend endpoints used:
 *   GET  /chat/rooms                     — list user's rooms
 *   GET  /chat/rooms/{id}                — room with recent messages
 *   GET  /chat/rooms/{id}/messages       — paginated history
 *   POST /chat/rooms/direct              — get-or-create DIRECT room (CONNECTED gate)
 *   POST /chat/rooms/{id}/messages       — REST send fallback
 *   WS   /chat/ws/{id}?token=...         — real-time
 */

import * as SecureStore from "expo-secure-store";
import api from "./api";
import { Config } from "../constants/config";
import {
  ChatRoom,
  ChatRoomDetail,
  ChatMessage,
  MessageListResponse,
  DirectRoomCreateRequest,
  SendMessageRequest,
  WSClientMessage,
  WSServerMessage,
  WSConnectionState,
} from "../types/chat";

// ============================================================
// REST SERVICE (object-literal pattern)
// ============================================================

export const chatService = {
  /**
   * GET /chat/rooms — list current user's chat rooms.
   */
  listRooms: async (limit: number = 50): Promise<ChatRoom[]> => {
    const response = await api.get<ChatRoom[]>("/chat/rooms", {
      params: { limit },
    });
    return response.data;
  },

  /**
   * GET /chat/rooms/{id} — fetch one room with the most recent messages embedded.
   */
  getRoom: async (roomId: string): Promise<ChatRoomDetail> => {
    const response = await api.get<ChatRoomDetail>(`/chat/rooms/${roomId}`);
    return response.data;
  },

  /**
   * GET /chat/rooms/{id}/messages — cursor-paginated history.
   * Returns newest-first. Pass `before` (ISO datetime of oldest received) for older pages.
   */
  getMessages: async (
    roomId: string,
    options: { limit?: number; before?: string | null } = {},
  ): Promise<MessageListResponse> => {
    const { limit = 50, before } = options;
    const params: Record<string, string | number> = { limit };
    if (before) params.before = before;
    const response = await api.get<MessageListResponse>(
      `/chat/rooms/${roomId}/messages`,
      { params },
    );
    return response.data;
  },

  /**
   * POST /chat/rooms/direct — get-or-create a DIRECT room with another user.
   *
   * **Requires the other user to be CONNECTED.**
   * Throws 403 with a friendly detail message if they aren't yet.
   */
  openDirectRoom: async (otherUserId: string): Promise<ChatRoomDetail> => {
    const body: DirectRoomCreateRequest = { other_user_id: otherUserId };
    const response = await api.post<ChatRoomDetail>("/chat/rooms/direct", body);
    return response.data;
  },

  /**
   * POST /chat/rooms/{id}/messages — REST send fallback.
   * Use when the WebSocket isn't connected. Server still broadcasts to live WS clients.
   */
  sendMessageREST: async (
    roomId: string,
    content: string,
  ): Promise<ChatMessage> => {
    const body: SendMessageRequest = { content };
    const response = await api.post<ChatMessage>(
      `/chat/rooms/${roomId}/messages`,
      body,
    );
    return response.data;
  },
};

// ============================================================
// WS URL HELPER
// ============================================================

/**
 * Convert the REST API URL into a WebSocket URL.
 *   http://...   → ws://...
 *   https://...  → wss://...
 */
export function buildWSUrl(roomId: string, token: string): string {
  const wsBase = Config.API_URL.replace(/^http:\/\//, "ws://").replace(
    /^https:\/\//,
    "wss://",
  );
  return `${wsBase}/chat/ws/${roomId}?token=${encodeURIComponent(token)}`;
}

// ============================================================
// WEBSOCKET CLIENT
// ============================================================

export interface WebSocketClientOptions {
  roomId: string;
  /** Called when the connection state changes. */
  onStateChange?: (state: WSConnectionState) => void;
  /** Called for every server-to-client frame. */
  onFrame?: (frame: WSServerMessage) => void;
  /** Called once when fully closed (no more reconnect attempts). */
  onClosed?: (code: number, reason: string) => void;
}

/** Reconnect delays in ms — exponential-ish backoff capped at 30s. */
const RECONNECT_DELAYS_MS = [1000, 2000, 5000, 10000, 30000];

/**
 * Manages a single WebSocket connection to a chat room.
 *
 * RESPONSIBILITIES:
 *   - Read access_token from SecureStore on each connect/reconnect (so token rotation works)
 *   - Reconnect with exponential backoff on transient drops
 *   - DON'T reconnect on auth/forbidden/room-not-found close codes (terminal)
 *   - Queue outgoing messages while disconnected; flush on reconnect
 *   - Single source of truth for connection state via onStateChange
 *
 * USAGE:
 *   const client = new WebSocketClient({
 *     roomId: "abc",
 *     onFrame: (frame) => { ... },
 *     onStateChange: (state) => { ... },
 *   });
 *   await client.connect();
 *   client.send({ type: "message", content: "hello" });
 *   client.close();  // when leaving the screen
 */
export class WebSocketClient {
  private ws: WebSocket | null = null;
  private opts: WebSocketClientOptions;

  private state: WSConnectionState = "idle";
  private reconnectAttempt = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private isManualClose = false;
  private outgoingQueue: WSClientMessage[] = [];

  // Close codes that are TERMINAL — never retry
  private static TERMINAL_CODES = new Set([4001, 4003, 4004, 4005]);

  constructor(opts: WebSocketClientOptions) {
    this.opts = opts;
  }

  // ---------- Public API ----------

  /** Open the connection. Idempotent — calling while connected is a no-op. */
  async connect(): Promise<void> {
    if (this.state === "connecting" || this.state === "connected") return;
    this.isManualClose = false;
    await this._open();
  }

  /** Send a frame. Queues if not connected. */
  send(frame: WSClientMessage): void {
    if (this.state === "connected" && this.ws?.readyState === 1 /* OPEN */) {
      try {
        this.ws.send(JSON.stringify(frame));
      } catch (e) {
        if (__DEV__) console.warn("[WS] send failed; queuing", e);
        this.outgoingQueue.push(frame);
      }
    } else {
      this.outgoingQueue.push(frame);
    }
  }

  /** Send a ping for keepalive. */
  ping(): void {
    this.send({ type: "ping" });
  }

  /** Close the connection permanently. No reconnect. */
  close(): void {
    this.isManualClose = true;
    this._clearReconnectTimer();
    if (this.ws) {
      try {
        this.ws.close(1000, "Manual close");
      } catch {
        /* noop */
      }
      this.ws = null;
    }
    this._setState("closed");
  }

  getState(): WSConnectionState {
    return this.state;
  }

  // ---------- Internals ----------

  private async _open(): Promise<void> {
    this._setState(this.reconnectAttempt > 0 ? "reconnecting" : "connecting");

    const token = await SecureStore.getItemAsync("access_token");
    if (!token) {
      if (__DEV__) console.warn("[WS] no access_token in SecureStore — abort");
      this._setState("closed");
      this.opts.onClosed?.(4001, "Missing token");
      return;
    }

    const url = buildWSUrl(this.opts.roomId, token);
    if (__DEV__)
      console.log(`[WS] connecting ${this.opts.roomId.slice(0, 8)}...`);

    try {
      this.ws = new WebSocket(url);
    } catch (e) {
      if (__DEV__) console.warn("[WS] WebSocket() threw:", e);
      this._scheduleReconnect();
      return;
    }

    this.ws.onopen = () => {
      if (__DEV__) console.log(`[WS] open ${this.opts.roomId.slice(0, 8)}`);
      this.reconnectAttempt = 0;
      this._setState("connected");
      this._flushQueue();
    };

    this.ws.onmessage = (ev: WebSocketMessageEvent) => {
      try {
        const frame: WSServerMessage = JSON.parse(ev.data as string);
        this.opts.onFrame?.(frame);
      } catch (e) {
        if (__DEV__) console.warn("[WS] bad frame:", e);
      }
    };

    this.ws.onerror = (ev) => {
      if (__DEV__) console.warn("[WS] error", ev);
      // Don't change state here — onclose will follow
    };

    this.ws.onclose = (ev: WebSocketCloseEvent) => {
      const code = ev.code ?? 1006;
      const reason = ev.reason ?? "";
      if (__DEV__) {
        console.log(
          `[WS] closed ${this.opts.roomId.slice(0, 8)} code=${code} reason="${reason}"`,
        );
      }
      this.ws = null;

      if (this.isManualClose) {
        this._setState("closed");
        return;
      }

      // Terminal close codes → never retry
      if (WebSocketClient.TERMINAL_CODES.has(code)) {
        this._setState("closed");
        this.opts.onClosed?.(code, reason);
        return;
      }

      // Otherwise schedule reconnect
      this._scheduleReconnect();
    };
  }

  private _scheduleReconnect(): void {
    this._clearReconnectTimer();
    const idx = Math.min(this.reconnectAttempt, RECONNECT_DELAYS_MS.length - 1);
    const delay = RECONNECT_DELAYS_MS[idx];
    this.reconnectAttempt += 1;
    this._setState("reconnecting");
    if (__DEV__) {
      console.log(
        `[WS] reconnect in ${delay}ms (attempt ${this.reconnectAttempt})`,
      );
    }
    this.reconnectTimer = setTimeout(() => {
      this._open();
    }, delay);
  }

  private _clearReconnectTimer(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  private _flushQueue(): void {
    while (this.outgoingQueue.length > 0 && this.ws?.readyState === 1) {
      const frame = this.outgoingQueue.shift()!;
      try {
        this.ws.send(JSON.stringify(frame));
      } catch (e) {
        if (__DEV__) console.warn("[WS] flush send failed; re-queuing", e);
        this.outgoingQueue.unshift(frame);
        return;
      }
    }
  }

  private _setState(s: WSConnectionState): void {
    if (this.state === s) return;
    this.state = s;
    this.opts.onStateChange?.(s);
  }
}
