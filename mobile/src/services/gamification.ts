/**
 * LAYERS — Gamification Service
 * ==========================================
 * PATTERN: object-literal service (same as questService / connectionService).
 */

import api from "./api";
import {
  BadgesResponse,
  LeaderboardResponse,
  LeaderboardScope,
} from "../types/gamification";

export const gamificationService = {
  /** All badges with unlocked state. */
  getBadges: async (): Promise<BadgesResponse> => {
    const response = await api.get<BadgesResponse>("/badges/me");
    return response.data;
  },

  /** Re-evaluate badges server-side; returns newly unlocked. */
  syncBadges: async (): Promise<{
    unlocked: { id: string; title: string; icon: string }[];
  }> => {
    const response = await api.post("/badges/sync");
    return response.data;
  },

  /** Ranked leaderboard for a scope. */
  getLeaderboard: async (
    scope: LeaderboardScope = "global",
    limit = 50,
  ): Promise<LeaderboardResponse> => {
    const response = await api.get<LeaderboardResponse>("/leaderboard", {
      params: { scope, limit },
    });
    return response.data;
  },
};
