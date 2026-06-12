/**
 * LAYERS — Badge Store
 */

import { create } from "zustand";
import { gamificationService } from "../services/gamification";
import { BadgeItem } from "../types/gamification";

interface BadgeState {
  badges: BadgeItem[];
  unlockedCount: number;
  total: number;
  isLoading: boolean;
  error: string | null;

  fetch: () => Promise<void>;
  /** Ask the server to re-check criteria, then refresh. */
  sync: () => Promise<{ id: string; title: string; icon: string }[]>;
}

export const useBadgeStore = create<BadgeState>((set) => ({
  badges: [],
  unlockedCount: 0,
  total: 0,
  isLoading: false,
  error: null,

  fetch: async () => {
    set({ isLoading: true, error: null });
    try {
      const data = await gamificationService.getBadges();
      set({
        badges: data.badges,
        unlockedCount: data.unlocked_count,
        total: data.total,
        isLoading: false,
      });
    } catch (e: any) {
      set({
        error:
          e?.response?.data?.detail ?? e?.message ?? "Failed to load badges",
        isLoading: false,
      });
    }
  },

  sync: async () => {
    try {
      const res = await gamificationService.syncBadges();
      // refresh the grid after syncing
      const data = await gamificationService.getBadges();
      set({
        badges: data.badges,
        unlockedCount: data.unlocked_count,
        total: data.total,
      });
      return res.unlocked;
    } catch {
      return [];
    }
  },
}));
