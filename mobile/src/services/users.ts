/**
 * LAYERS — Users Service
 * ==========================================
 * Block management + permanent account deletion.
 *
 * PATTERN: object-literal service (same as inboxService) — classes are
 * only for stateful things like the WebSocket client.
 *
 * Backend endpoints (Week 9 Day 3):
 *   GET    /users/me/blocks
 *   POST   /users/{id}/block
 *   DELETE /users/{id}/block
 *   POST   /auth/me/delete        — permanent deletion (password confirm)
 */

import api from "./api";

// ============================================================
// TYPES
// ============================================================

export interface BlockedUser {
  user_id: string;
  username: string;
  avatar_url: string | null;
  blocked_at: string;
}

export interface BlocksResponse {
  items: BlockedUser[];
  total: number;
}

// ============================================================
// SERVICE
// ============================================================

export const usersService = {
  /** All users the current user has blocked, newest first. */
  getBlocks: async (): Promise<BlocksResponse> => {
    const response = await api.get<BlocksResponse>("/users/me/blocks");
    return response.data;
  },

  /** Block a user. Idempotent. They are never notified. */
  blockUser: async (userId: string): Promise<{ blocked: boolean; message: string }> => {
    const response = await api.post(`/users/${userId}/block`);
    return response.data;
  },

  /** Unblock a user. Idempotent. */
  unblockUser: async (userId: string): Promise<{ blocked: boolean; message: string }> => {
    const response = await api.delete(`/users/${userId}/block`);
    return response.data;
  },

  /**
   * PERMANENTLY delete the current account.
   * Backend anonymizes PII, marks artifacts DELETED, deactivates the row.
   * Requires the current password. THIS CANNOT BE UNDONE.
   */
  deleteAccount: async (password: string): Promise<{ message: string }> => {
    const response = await api.post("/auth/me/delete", { password });
    return response.data;
  },
};
