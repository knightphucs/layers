/**
 * LAYERS — Social Spark Store
 * ============================================
 * Zustand store for the boost / wave / synchronicity trio.
 *
 * STATE:
 *   boostQuota              — remaining boosts today
 *   boostedNearby           — boosted artifacts to merge into the map
 *   wavesNearbyCount        — anonymous count for the wave button badge
 *   pendingSync             — a synchronicity to show in a modal (set by discover)
 *
 * ACTIONS:
 *   fetchBoostQuota()
 *   boostArtifact(artifactId)
 *   fetchBoostedNearby(lat, lng)
 *   wave(lat, lng)
 *   fetchWavesNearby(lat, lng)
 *   discover(artifactId, lat?, lng?)   — call on artifact unlock
 *   dismissSync()
 *   clearError()
 */

import { create } from "zustand";
import { socialSparkService } from "../services/social_spark";
import {
  BoostQuota,
  BoostedArtifactItem,
  SynchronicityMatch,
} from "../types/social_spark";

interface SocialSparkState {
  // ---- State ----
  boostQuota: BoostQuota | null;
  boostedNearby: BoostedArtifactItem[];
  wavesNearbyCount: number;
  lastWaveResult: { others: number; wavedBack: boolean } | null;
  pendingSync: SynchronicityMatch | null;

  isBoosting: boolean;
  isWaving: boolean;
  error: string | null;

  // ---- Actions ----
  fetchBoostQuota: () => Promise<void>;
  boostArtifact: (artifactId: string) => Promise<boolean>;
  fetchBoostedNearby: (lat: number, lng: number) => Promise<void>;
  wave: (lat: number, lng: number) => Promise<void>;
  fetchWavesNearby: (lat: number, lng: number) => Promise<void>;
  discover: (artifactId: string, lat?: number, lng?: number) => Promise<void>;
  dismissSync: () => void;
  clearError: () => void;
}

export const useSocialSparkStore = create<SocialSparkState>((set, get) => ({
  boostQuota: null,
  boostedNearby: [],
  wavesNearbyCount: 0,
  lastWaveResult: null,
  pendingSync: null,

  isBoosting: false,
  isWaving: false,
  error: null,

  // ============================================================
  // 📡 Boost
  // ============================================================
  fetchBoostQuota: async () => {
    try {
      const quota = await socialSparkService.getBoostQuota();
      set({ boostQuota: quota });
    } catch (e: any) {
      if (__DEV__) console.warn("[spark] fetchBoostQuota failed:", e);
    }
  },

  boostArtifact: async (artifactId) => {
    set({ isBoosting: true, error: null });
    try {
      await socialSparkService.boostArtifact(artifactId);
      // Refresh quota after a successful boost
      await get().fetchBoostQuota();
      set({ isBoosting: false });
      return true;
    } catch (e: any) {
      set({
        error: e?.response?.data?.detail || "Couldn't boost this memory",
        isBoosting: false,
      });
      return false;
    }
  },

  fetchBoostedNearby: async (lat, lng) => {
    try {
      const resp = await socialSparkService.getBoostedNearby(lat, lng);
      set({ boostedNearby: resp.items });
    } catch (e: any) {
      if (__DEV__) console.warn("[spark] fetchBoostedNearby failed:", e);
    }
  },

  // ============================================================
  // 👋 Wave
  // ============================================================
  wave: async (lat, lng) => {
    set({ isWaving: true, error: null });
    try {
      const result = await socialSparkService.wave(lat, lng);
      set({
        isWaving: false,
        lastWaveResult: {
          others: result.others_waving_nearby,
          wavedBack: result.waved_back,
        },
      });
    } catch (e: any) {
      set({
        error: e?.response?.data?.detail || "Couldn't wave right now",
        isWaving: false,
      });
    }
  },

  fetchWavesNearby: async (lat, lng) => {
    try {
      const resp = await socialSparkService.getWavesNearby(lat, lng);
      set({ wavesNearbyCount: resp.count });
    } catch (e: any) {
      if (__DEV__) console.warn("[spark] fetchWavesNearby failed:", e);
    }
  },

  // ============================================================
  // ✨ Synchronicity
  // ============================================================
  discover: async (artifactId, lat, lng) => {
    try {
      const resp = await socialSparkService.discoverArtifact(
        artifactId,
        lat,
        lng,
      );
      if (resp.synchronicity) {
        set({ pendingSync: resp.synchronicity });
      }
    } catch (e: any) {
      // Discovery is best-effort — don't surface errors to the user
      if (__DEV__) console.warn("[spark] discover failed:", e);
    }
  },

  dismissSync: () => set({ pendingSync: null }),

  clearError: () => set({ error: null }),
}));
