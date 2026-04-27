/**
 * LAYERS — Connection Store
 * ==========================================
 * Zustand store managing connection state.
 *
 * PATTERN: Same as inboxStore, notificationStore.
 *
 * Features:
 *   - Level-based filtering (STRANGER, SIGNAL, CONNECTED)
 *   - Stats for profile screen
 *   - Optimistic upgrade actions
 *   - Pull-to-refresh
 */

import { create } from "zustand";
import { connectionService } from "../services/connections";
import {
  ConnectionItem,
  ConnectionLevel,
  ConnectionStatsResponse,
} from "../types/connections";

// ============================================================
// STATE
// ============================================================

interface ConnectionState {
  // Data
  connections: ConnectionItem[];
  stats: ConnectionStatsResponse | null;

  // Counts
  strangersCount: number;
  signalsCount: number;
  connectedCount: number;
  total: number;

  // Filter
  filter: ConnectionLevel | "all";

  // UI state
  isLoading: boolean;
  isRefreshing: boolean;
  error: string | null;

  // Actions
  fetchConnections: () => Promise<void>;
  refresh: () => Promise<void>;
  fetchStats: () => Promise<void>;
  setFilter: (filter: ConnectionLevel | "all") => void;
  requestUpgrade: (connectionId: string) => Promise<boolean>;
  acceptUpgrade: (connectionId: string) => Promise<boolean>;
  rejectUpgrade: (connectionId: string) => Promise<boolean>;
  clearError: () => void;
  reset: () => void;
}

// ============================================================
// STORE
// ============================================================

export const useConnectionStore = create<ConnectionState>((set, get) => ({
  connections: [],
  stats: null,
  strangersCount: 0,
  signalsCount: 0,
  connectedCount: 0,
  total: 0,
  filter: "all",
  isLoading: false,
  isRefreshing: false,
  error: null,

  // ========================================================
  // FETCH CONNECTIONS
  // ========================================================
  fetchConnections: async () => {
    const { filter, isLoading } = get();
    if (isLoading) return;

    set({ isLoading: true, error: null });

    try {
      const response = await connectionService.listConnections({
        level: filter === "all" ? undefined : filter,
        limit: 100,
      });

      set({
        connections: response.connections,
        total: response.total,
        strangersCount: response.strangers_count,
        signalsCount: response.signals_count,
        connectedCount: response.connected_count,
        isLoading: false,
      });
    } catch (error: any) {
      set({
        isLoading: false,
        error: error?.message || "Failed to load connections",
      });
    }
  },

  // ========================================================
  // REFRESH
  // ========================================================
  refresh: async () => {
    set({ isRefreshing: true });
    try {
      const { filter } = get();
      const response = await connectionService.listConnections({
        level: filter === "all" ? undefined : filter,
        limit: 100,
      });

      set({
        connections: response.connections,
        total: response.total,
        strangersCount: response.strangers_count,
        signalsCount: response.signals_count,
        connectedCount: response.connected_count,
        isRefreshing: false,
        error: null,
      });
    } catch (error: any) {
      set({ isRefreshing: false });
    }
  },

  // ========================================================
  // FETCH STATS
  // ========================================================
  fetchStats: async () => {
    try {
      const stats = await connectionService.getStats();
      set({ stats });
    } catch (error) {
      console.warn("Failed to fetch connection stats:", error);
    }
  },

  // ========================================================
  // FILTER
  // ========================================================
  setFilter: (filter) => {
    set({ filter, connections: [] });
    get().fetchConnections();
  },

  // ========================================================
  // REQUEST UPGRADE — Optimistic
  // ========================================================
  requestUpgrade: async (connectionId: string) => {
    try {
      const response = await connectionService.requestUpgrade(connectionId);

      // Optimistic update
      set((state) => ({
        connections: state.connections.map((c) =>
          c.id === connectionId
            ? {
                ...c,
                upgrade_requested_by_me: true,
                // If server says upgraded, update status + level
                ...(response.upgraded && {
                  status: "CONNECTED" as const,
                  level: "CONNECTED" as ConnectionLevel,
                }),
              }
            : c,
        ),
      }));

      // Refetch stats if upgrade happened
      if (response.upgraded) {
        get().fetchStats();
      }

      return response.upgraded;
    } catch (error: any) {
      set({ error: error?.message || "Failed to request upgrade" });
      return false;
    }
  },

  // ========================================================
  // ACCEPT UPGRADE — Same as request
  // ========================================================
  acceptUpgrade: async (connectionId: string) => {
    return get().requestUpgrade(connectionId);
  },

  // ========================================================
  // REJECT UPGRADE
  // ========================================================
  rejectUpgrade: async (connectionId: string) => {
    try {
      await connectionService.rejectUpgrade(connectionId);

      set((state) => ({
        connections: state.connections.map((c) =>
          c.id === connectionId
            ? {
                ...c,
                upgrade_requested_by_me: false,
                upgrade_requested_by_them: false,
              }
            : c,
        ),
      }));

      return true;
    } catch (error: any) {
      set({ error: error?.message || "Failed to reject upgrade" });
      return false;
    }
  },

  clearError: () => set({ error: null }),

  reset: () =>
    set({
      connections: [],
      stats: null,
      strangersCount: 0,
      signalsCount: 0,
      connectedCount: 0,
      total: 0,
      filter: "all",
      isLoading: false,
      isRefreshing: false,
      error: null,
    }),
}));
