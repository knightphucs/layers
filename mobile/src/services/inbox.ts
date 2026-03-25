/**
 * LAYERS — Inbox Service
 * ==========================================
 * API calls for the Memory Inbox system.
 *
 * Backend endpoints used:
 *   GET  /artifacts/mine          — User's created artifacts (existing)
 *   GET  /artifacts/nearby        — Nearby artifacts (existing)
 *   GET  /artifacts/{id}          — Artifact detail (existing)
 *   POST /artifacts/{id}/reply    — Slow Mail reply (existing)
 *
 * NEW endpoints we'll add to backend (Day 2+):
 *   GET  /inbox                   — Received artifacts & replies
 *   GET  /inbox/stats             — Unread counts, pending replies
 *   PUT  /inbox/{id}/read         — Mark as read
 *
 */

import api from "./api";
import {
  InboxItem,
  InboxResponse,
  InboxStatsResponse,
  InboxCategory,
} from "../types/inbox";
import { Artifact } from "../types";

// ============================================================
// INBOX SERVICE
// ============================================================

export const inboxService = {
  /**
   * Fetch inbox items with cursor-based pagination.
   */
  getInbox: async (params: {
    category?: InboxCategory | "all";
    cursor?: string | null;
    limit?: number;
  }): Promise<InboxResponse> => {
    const { category = "all", cursor, limit = 20 } = params;

    // Build query params
    const queryParams: Record<string, string | number> = {
      limit,
      offset: cursor ? parseInt(cursor, 10) : 0,
    };

    // Filter by content type based on category
    if (category === "paper_planes") {
      queryParams.content_type = "PAPER_PLANE";
    } else if (category === "time_capsules") {
      queryParams.content_type = "TIME_CAPSULE";
    }

    try {
      // Use existing endpoint — GET /artifacts/mine returns user's artifacts
      // In production, this will be replaced by GET /inbox
      const response = await api.get<{
        items: Artifact[];
        total: number;
      }>("/artifacts/mine", { params: queryParams });

      const items: InboxItem[] = response.data.items.map((artifact) => ({
        id: artifact.id,
        artifact,
        sender: artifact.creator_username
          ? {
              id: artifact.user_id,
              username: artifact.creator_username,
              avatar_url: artifact.creator_avatar || undefined,
            }
          : undefined,
        is_read: (artifact.view_count ?? 0) > 0,
        received_at: artifact.created_at,
        read_at: null,
      }));

      const nextOffset = (cursor ? parseInt(cursor, 10) : 0) + items.length;

      return {
        items,
        total: response.data.total,
        unread_count: items.filter((i) => !i.is_read).length,
        cursor: items.length < limit ? null : String(nextOffset),
      };
    } catch (error) {
      console.error("Failed to fetch inbox:", error);
      throw error;
    }
  },

  /**
   * Get inbox statistics (unread counts, pending replies).
   * For MVP: computed client-side from artifacts data.
   */
  getStats: async (): Promise<InboxStatsResponse> => {
    try {
      const response = await api.get<{
        items: Artifact[];
        total: number;
      }>("/artifacts/mine", { params: { limit: 100, offset: 0 } });

      const artifacts = response.data.items;

      return {
        total_received: response.data.total,
        unread_count: artifacts.filter((a) => (a.view_count ?? 0) === 0).length,
        replies_pending: artifacts.reduce(
          (sum, a) => sum + (a.reply_count ?? 0),
          0,
        ),
        paper_planes_found: artifacts.filter(
          (a) => a.content_type === "PAPER_PLANE",
        ).length,
        time_capsules_waiting: artifacts.filter(
          (a) =>
            a.content_type === "TIME_CAPSULE" &&
            a.unlock_at &&
            new Date(a.unlock_at) > new Date(),
        ).length,
      };
    } catch (error) {
      console.error("Failed to fetch inbox stats:", error);
      throw error;
    }
  },

  /**
   * Mark an inbox item as read.
   * For MVP: calls GET /artifacts/{id} which increments view_count.
   */
  markAsRead: async (artifactId: string): Promise<void> => {
    try {
      // Viewing the artifact detail increments view_count on backend
      await api.get(`/artifacts/${artifactId}`);
    } catch (error) {
      // Non-critical — don't throw
      console.warn("Failed to mark as read:", error);
    }
  },

  /**
   * Get artifact detail for reading a letter.
   * Requires lat/lng for Proof of Presence check.
   */
  getArtifactDetail: async (
    artifactId: string,
    lat?: number,
    lng?: number,
  ): Promise<Artifact> => {
    const params: Record<string, number> = {};
    if (lat !== undefined && lng !== undefined) {
      params.lat = lat;
      params.lng = lng;
    }
    const response = await api.get<Artifact>(`/artifacts/${artifactId}`, {
      params,
    });
    return response.data;
  },

  /**
   * Send a Slow Mail reply to an artifact.
   * Reply will be delivered in 6-12 hours.
   */
  sendReply: async (
    artifactId: string,
    content: string,
    lat: number,
    lng: number,
  ): Promise<{
    id: string;
    deliver_at: string;
    message: string;
  }> => {
    const response = await api.post(
      `/artifacts/${artifactId}/reply`,
      { content },
      { params: { lat, lng } },
    );
    return response.data;
  },
};
