/**
 * LAYERS — Leaderboard Store
 */

import { create } from "zustand";
import { gamificationService } from "../services/gamification";
import { LeaderboardEntry, LeaderboardScope } from "../types/gamification";

interface LeaderboardState {
  scope: LeaderboardScope;
  entries: LeaderboardEntry[];
  myRank: number | null;
  myScore: number;
  isLoading: boolean;
  error: string | null;

  setScope: (scope: LeaderboardScope) => void;
  fetch: () => Promise<void>;
}

export const useLeaderboardStore = create<LeaderboardState>((set, get) => ({
  scope: "global",
  entries: [],
  myRank: null,
  myScore: 0,
  isLoading: false,
  error: null,

  setScope: (scope) => {
    set({ scope });
    get().fetch();
  },

  fetch: async () => {
    set({ isLoading: true, error: null });
    try {
      const data = await gamificationService.getLeaderboard(get().scope);
      set({
        entries: data.entries,
        myRank: data.my_rank ?? null,
        myScore: data.my_score,
        isLoading: false,
      });
    } catch (e: any) {
      set({
        error:
          e?.response?.data?.detail ??
          e?.message ??
          "Failed to load leaderboard",
        isLoading: false,
      });
    }
  },
}));
