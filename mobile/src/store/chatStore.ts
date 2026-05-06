/**
 * LAYERS — Chat Store (Week 6 Day 2)
 * ===================================
 * Zustand store for chat state.
 *
 * STATE:
 *   - rooms                 — list view (sorted by last_activity_at desc)
 *   - messagesByRoom        — keyed cache of messages, newest first
 *   - cursorByRoom          — pagination cursors
 *   - hasMoreByRoom         — whether more old messages exist per room
 *   - activeRoomId          — currently open chat (null = list view)
 *   - wsClient              — single in-flight WebSocketClient
 *   - wsState               — current connection state for UI
 *
 * ACTIONS:
 *   - fetchRooms()                       — refresh /chat/rooms
 *   - openChatWithUser(otherUserId)      — POST /chat/rooms/direct + navigate
 *   - openChatWithRoom(roomId)           — navigate by roomId (room must already exist)
 *   - leaveChat()                        — close WS + clear activeRoomId
 *   - sendMessage(roomId, content)       — optimistic local + WS send (REST fallback)
 *   - loadOlderMessages(roomId)          — paginate
 *   - clearError()
 *   - reset()
 *
 * PATTERN: Same as inboxStore, connectionStore.
 */

import { create } from "zustand";
import { chatService, WebSocketClient } from "../services/chat";
import {
  ChatMessage,
  ChatMessageWithStatus,
  ChatRoom,
  ChatRoomDetail,
  ChatRoomItem,
  WSConnectionState,
  WSServerMessage,
} from "../types/chat";

// ============================================================
// HELPERS
// ============================================================

function genClientId(): string {
  return `local-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function deriveOtherUserId(
  room: ChatRoom,
  currentUserId: string,
): string | null {
  if (room.user_a_id && room.user_b_id) {
    return room.user_a_id === currentUserId ? room.user_b_id : room.user_a_id;
  }
  return null;
}

/**
 * Insert a message into the (newest-first) cache, deduping by id and
 * keeping it sorted by created_at desc.
 */
function insertMessage(
  list: ChatMessageWithStatus[],
  msg: ChatMessageWithStatus,
): ChatMessageWithStatus[] {
  // Dedupe by server id OR by client_id (replace optimistic with canonical)
  const filtered = list.filter((m) => {
    if (msg.id && m.id === msg.id) return false;
    if (msg.client_id && m.client_id === msg.client_id) return false;
    return true;
  });
  // Insert in correct sort position (newest first)
  const inserted = [...filtered, msg].sort((a, b) =>
    a.created_at < b.created_at ? 1 : -1,
  );
  return inserted;
}

// ============================================================
// STORE
// ============================================================

interface ChatState {
  // ---- State ----
  rooms: ChatRoomItem[];
  messagesByRoom: Record<string, ChatMessageWithStatus[]>;
  cursorByRoom: Record<string, string | null>;
  hasMoreByRoom: Record<string, boolean>;

  activeRoomId: string | null;
  wsClient: WebSocketClient | null;
  wsState: WSConnectionState;

  isLoadingRooms: boolean;
  isLoadingMessages: boolean;
  isOpeningChat: boolean;
  error: string | null;

  // ---- Actions ----
  fetchRooms: (currentUserId: string) => Promise<void>;
  openChatWithUser: (
    otherUserId: string,
    currentUserId: string,
  ) => Promise<string | null>;
  openChatWithRoom: (roomId: string, currentUserId: string) => Promise<void>;
  leaveChat: () => void;
  sendMessage: (
    roomId: string,
    content: string,
    senderId: string,
  ) => Promise<void>;
  loadOlderMessages: (roomId: string) => Promise<void>;
  clearError: () => void;
  reset: () => void;

  // ---- Internal helpers (not part of public API but useful) ----
  _handleFrame: (frame: WSServerMessage) => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  // ---- Initial state ----
  rooms: [],
  messagesByRoom: {},
  cursorByRoom: {},
  hasMoreByRoom: {},

  activeRoomId: null,
  wsClient: null,
  wsState: "idle",

  isLoadingRooms: false,
  isLoadingMessages: false,
  isOpeningChat: false,
  error: null,

  // ============================================================
  // fetchRooms
  // ============================================================
  fetchRooms: async (currentUserId) => {
    set({ isLoadingRooms: true, error: null });
    try {
      const rooms = await chatService.listRooms();
      const items: ChatRoomItem[] = rooms.map((r) => ({
        ...r,
        other_user_id: deriveOtherUserId(r, currentUserId),
      }));
      set({ rooms: items, isLoadingRooms: false });
    } catch (e: any) {
      set({
        error: e?.response?.data?.detail || "Failed to load chats",
        isLoadingRooms: false,
      });
    }
  },

  // ============================================================
  // openChatWithUser — POST /chat/rooms/direct, then enter chat
  // ============================================================
  openChatWithUser: async (otherUserId, currentUserId) => {
    set({ isOpeningChat: true, error: null });
    try {
      const detail: ChatRoomDetail =
        await chatService.openDirectRoom(otherUserId);

      // Cache room + recent messages
      const item: ChatRoomItem = {
        ...detail,
        other_user_id: deriveOtherUserId(detail, currentUserId),
      };
      const recent: ChatMessageWithStatus[] = (
        detail.recent_messages || []
      ).map((m) => ({ ...m, status: "sent" }));

      set((state) => {
        // Upsert in rooms list
        const existing = state.rooms.findIndex((r) => r.id === item.id);
        const nextRooms =
          existing >= 0
            ? state.rooms.map((r) => (r.id === item.id ? item : r))
            : [item, ...state.rooms];
        return {
          rooms: nextRooms,
          messagesByRoom: { ...state.messagesByRoom, [item.id]: recent },
          isOpeningChat: false,
          activeRoomId: item.id,
        };
      });

      // Open WebSocket
      get().openChatWithRoom(item.id, currentUserId);

      return item.id;
    } catch (e: any) {
      const detail = e?.response?.data?.detail || "Failed to open chat";
      set({ error: detail, isOpeningChat: false });
      return null;
    }
  },

  // ============================================================
  // openChatWithRoom — opens WS + sets activeRoomId
  // ============================================================
  openChatWithRoom: async (roomId, currentUserId) => {
    // Close any existing WS first
    const existing = get().wsClient;
    if (existing) existing.close();

    // Make sure recent messages are cached if not already
    if (!get().messagesByRoom[roomId]) {
      try {
        const detail = await chatService.getRoom(roomId);
        const item: ChatRoomItem = {
          ...detail,
          other_user_id: deriveOtherUserId(detail, currentUserId),
        };
        const recent: ChatMessageWithStatus[] = (
          detail.recent_messages || []
        ).map((m) => ({ ...m, status: "sent" }));
        set((state) => {
          const existingIdx = state.rooms.findIndex((r) => r.id === item.id);
          const nextRooms =
            existingIdx >= 0
              ? state.rooms.map((r) => (r.id === item.id ? item : r))
              : [item, ...state.rooms];
          return {
            rooms: nextRooms,
            messagesByRoom: { ...state.messagesByRoom, [roomId]: recent },
          };
        });
      } catch (e: any) {
        set({ error: e?.response?.data?.detail || "Failed to load chat" });
        return;
      }
    }

    // Spin up WS
    const client = new WebSocketClient({
      roomId,
      onStateChange: (state) => set({ wsState: state }),
      onFrame: (frame) => get()._handleFrame(frame),
      onClosed: (code, reason) => {
        if (__DEV__)
          console.log(`[chatStore] WS terminal close: ${code} ${reason}`);
        // Don't auto-clear activeRoomId on terminal close — let UI show error banner
      },
    });

    set({ wsClient: client, activeRoomId: roomId });
    client.connect();
  },

  // ============================================================
  // leaveChat — called when navigating away
  // ============================================================
  leaveChat: () => {
    const client = get().wsClient;
    if (client) client.close();
    set({ wsClient: null, wsState: "idle", activeRoomId: null });
  },

  // ============================================================
  // sendMessage — optimistic local + WS-or-REST send
  // ============================================================
  sendMessage: async (roomId, content, senderId) => {
    const trimmed = content.trim();
    if (!trimmed) return;

    const clientId = genClientId();
    const optimistic: ChatMessageWithStatus = {
      id: clientId, // temporary; replaced when server returns canonical id
      client_id: clientId,
      room_id: roomId,
      sender_id: senderId,
      content: trimmed,
      created_at: new Date().toISOString(),
      status: "sending",
    };

    // Insert optimistically
    set((state) => ({
      messagesByRoom: {
        ...state.messagesByRoom,
        [roomId]: insertMessage(state.messagesByRoom[roomId] || [], optimistic),
      },
    }));

    // Try WS first
    const client = get().wsClient;
    if (client && client.getState() === "connected") {
      // Fire-and-forget — server broadcast will return the canonical message,
      // and _handleFrame will replace the optimistic one (matched by content/sender if no client_id mapping)
      client.send({ type: "message", content: trimmed });
      // We can't tag WS sends with our client_id (server doesn't echo it),
      // so we mark the optimistic as "sent" once the broadcast lands. Until then,
      // it'll show "sending" — see _handleFrame for the swap logic.
      return;
    }

    // REST fallback
    try {
      const saved = await chatService.sendMessageREST(roomId, trimmed);
      // Replace optimistic with canonical
      set((state) => {
        const list = state.messagesByRoom[roomId] || [];
        // Remove the optimistic, add the canonical
        const filtered = list.filter((m) => m.client_id !== clientId);
        const updated: ChatMessageWithStatus = { ...saved, status: "sent" };
        return {
          messagesByRoom: {
            ...state.messagesByRoom,
            [roomId]: insertMessage(filtered, updated),
          },
        };
      });
    } catch (e: any) {
      // Mark optimistic as failed
      set((state) => {
        const list = state.messagesByRoom[roomId] || [];
        return {
          messagesByRoom: {
            ...state.messagesByRoom,
            [roomId]: list.map((m) =>
              m.client_id === clientId ? { ...m, status: "failed" } : m,
            ),
          },
          error: e?.response?.data?.detail || "Failed to send",
        };
      });
    }
  },

  // ============================================================
  // loadOlderMessages — cursor pagination
  // ============================================================
  loadOlderMessages: async (roomId) => {
    if (get().isLoadingMessages) return;
    if (get().hasMoreByRoom[roomId] === false) return;

    set({ isLoadingMessages: true });
    try {
      const cursor = get().cursorByRoom[roomId] ?? null;
      const list = get().messagesByRoom[roomId] || [];
      // If no explicit cursor yet, derive from oldest cached message
      const before =
        cursor ?? (list.length > 0 ? list[list.length - 1].created_at : null);

      const resp = await chatService.getMessages(roomId, {
        limit: 50,
        before,
      });

      set((state) => {
        const merged = [...(state.messagesByRoom[roomId] || [])];
        for (const m of resp.items) {
          const idx = merged.findIndex((x) => x.id === m.id);
          if (idx === -1) merged.push({ ...m, status: "sent" });
        }
        // Re-sort newest first
        merged.sort((a, b) => (a.created_at < b.created_at ? 1 : -1));

        return {
          messagesByRoom: { ...state.messagesByRoom, [roomId]: merged },
          cursorByRoom: { ...state.cursorByRoom, [roomId]: resp.next_cursor },
          hasMoreByRoom: { ...state.hasMoreByRoom, [roomId]: resp.has_more },
          isLoadingMessages: false,
        };
      });
    } catch (e: any) {
      set({
        error: e?.response?.data?.detail || "Failed to load older messages",
        isLoadingMessages: false,
      });
    }
  },

  clearError: () => set({ error: null }),

  reset: () => {
    const client = get().wsClient;
    if (client) client.close();
    set({
      rooms: [],
      messagesByRoom: {},
      cursorByRoom: {},
      hasMoreByRoom: {},
      activeRoomId: null,
      wsClient: null,
      wsState: "idle",
      isLoadingRooms: false,
      isLoadingMessages: false,
      isOpeningChat: false,
      error: null,
    });
  },

  // ============================================================
  // _handleFrame — internal: route incoming WS frames
  // ============================================================
  _handleFrame: (frame) => {
    if (frame.type === "message") {
      const incoming: ChatMessageWithStatus = { ...frame.data, status: "sent" };
      set((state) => {
        const roomId = incoming.room_id;
        const list = state.messagesByRoom[roomId] || [];

        // Try to match an optimistic local-only message by content + sender + within 30s
        // (we can't use client_id because the server doesn't echo it).
        const candidateIdx = list.findIndex(
          (m) =>
            m.client_id !== undefined &&
            m.sender_id === incoming.sender_id &&
            m.content === incoming.content &&
            Math.abs(
              new Date(m.created_at).getTime() -
                new Date(incoming.created_at).getTime(),
            ) < 30_000,
        );

        let nextList: ChatMessageWithStatus[];
        if (candidateIdx >= 0) {
          // Replace optimistic with canonical
          const filtered = list.filter((_, i) => i !== candidateIdx);
          nextList = insertMessage(filtered, incoming);
        } else {
          // Insert as new
          nextList = insertMessage(list, incoming);
        }

        // Bump the room's last_activity_at in the rooms list and re-sort
        const nextRooms = state.rooms
          .map((r) =>
            r.id === roomId
              ? {
                  ...r,
                  last_activity_at: incoming.created_at,
                  message_count: r.message_count + 1,
                  last_message_preview: incoming.content,
                }
              : r,
          )
          .sort((a, b) => (a.last_activity_at < b.last_activity_at ? 1 : -1));

        return {
          messagesByRoom: { ...state.messagesByRoom, [roomId]: nextList },
          rooms: nextRooms,
        };
      });
      return;
    }

    if (frame.type === "presence") {
      // Day 5 polish will use this for "X is here" indicators
      if (__DEV__)
        console.log(
          `[chatStore] presence ${frame.event} from ${frame.user_id}`,
        );
      return;
    }

    if (frame.type === "error") {
      if (__DEV__)
        console.warn(
          `[chatStore] WS error frame: ${frame.code} — ${frame.message}`,
        );
      set({ error: frame.message });
      return;
    }

    // pong → ignore
  },
}));
