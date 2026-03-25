/**
 * LAYERS — Inbox Store
 * ==========================================
 * Zustand store managing inbox state.
 *
 * PATTERN: Same as authStore/locationStore —
 *   state + actions in a single create() call.
 *
 * Features:
 *   - Cursor-based pagination (load more on scroll)
 *   - Category filtering (all / received / replies / paper_planes / time_capsules)
 *   - Unread count for tab badge
 *   - Pull-to-refresh
 *   - Optimistic read marking
 */

import { create } from "zustand";
import { inboxService } from "../services/inbox";
import {
  InboxItem,
  InboxCategory,
  InboxFilters,
  InboxStatsResponse,
} from "../types/inbox";

// ============================================================
// STATE INTERFACE
// ============================================================

interface InboxState {
  // Data
  items: InboxItem[];
  stats: InboxStatsResponse | null;

  // Pagination
  cursor: string | null;
  hasMore: boolean;
  total: number;

  // UI State
  isLoading: boolean;
  isRefreshing: boolean;
  isLoadingMore: boolean;
  error: string | null;

  // Filters
  filters: InboxFilters;

  // Computed
  unreadCount: number;

  // Actions
  fetchInbox: () => Promise<void>;
  fetchMore: () => Promise<void>;
  refresh: () => Promise<void>;
  fetchStats: () => Promise<void>;
  markAsRead: (itemId: string) => void;
  setCategory: (category: InboxCategory | "all") => void;
  setReadFilter: (isRead: boolean | null) => void;
  clearError: () => void;
  reset: () => void;
}

// ============================================================
// STORE
// ============================================================

export const useInboxStore = create<InboxState>((set, get) => ({
  // Initial state
  items: [],
  stats: null,
  cursor: null,
  hasMore: true,
  total: 0,
  isLoading: false,
  isRefreshing: false,
  isLoadingMore: false,
  error: null,
  unreadCount: 0,
  filters: {
    category: "all",
    is_read: null,
  },

  // ========================================================
  // FETCH INBOX — Initial load
  // ========================================================
  fetchInbox: async () => {
    const { filters, isLoading } = get();
    if (isLoading) return;

    set({ isLoading: true, error: null });

    try {
      const response = await inboxService.getInbox({
        category: filters.category,
        cursor: null,
        limit: 20,
      });

      let items = response.items;

      // Apply client-side read filter
      if (filters.is_read !== null) {
        items = items.filter((i) => i.is_read === filters.is_read);
      }

      set({
        items,
        total: response.total,
        unreadCount: response.unread_count,
        cursor: response.cursor,
        hasMore: response.cursor !== null,
        isLoading: false,
      });
    } catch (error: any) {
      set({
        isLoading: false,
        error: error.message || "Failed to load inbox",
      });
    }
  },

  // ========================================================
  // FETCH MORE — Cursor pagination (infinite scroll)
  // ========================================================
  fetchMore: async () => {
    const { cursor, hasMore, isLoadingMore, filters } = get();
    if (!hasMore || isLoadingMore || !cursor) return;

    set({ isLoadingMore: true });

    try {
      const response = await inboxService.getInbox({
        category: filters.category,
        cursor,
        limit: 20,
      });

      let newItems = response.items;

      if (filters.is_read !== null) {
        newItems = newItems.filter((i) => i.is_read === filters.is_read);
      }

      set((state) => ({
        items: [...state.items, ...newItems],
        cursor: response.cursor,
        hasMore: response.cursor !== null,
        isLoadingMore: false,
      }));
    } catch (error: any) {
      set({ isLoadingMore: false });
    }
  },

  // ========================================================
  // REFRESH — Pull-to-refresh
  // ========================================================
  refresh: async () => {
    set({ isRefreshing: true });

    try {
      const { filters } = get();
      const response = await inboxService.getInbox({
        category: filters.category,
        cursor: null,
        limit: 20,
      });

      let items = response.items;
      if (filters.is_read !== null) {
        items = items.filter((i) => i.is_read === filters.is_read);
      }

      set({
        items,
        total: response.total,
        unreadCount: response.unread_count,
        cursor: response.cursor,
        hasMore: response.cursor !== null,
        isRefreshing: false,
        error: null,
      });
    } catch (error: any) {
      set({ isRefreshing: false });
    }
  },

  // ========================================================
  // FETCH STATS — Badge counts
  // ========================================================
  fetchStats: async () => {
    try {
      const stats = await inboxService.getStats();
      set({ stats, unreadCount: stats.unread_count });
    } catch (error) {
      // Non-critical — silently fail
      console.warn("Failed to fetch inbox stats:", error);
    }
  },

  // ========================================================
  // MARK AS READ — Optimistic update
  // ========================================================
  markAsRead: (itemId: string) => {
    set((state) => {
      const items = state.items.map((item) =>
        item.id === itemId
          ? { ...item, is_read: true, read_at: new Date().toISOString() }
          : item,
      );
      const unreadCount = items.filter((i) => !i.is_read).length;
      return { items, unreadCount };
    });

    // Fire-and-forget backend call
    inboxService.markAsRead(itemId).catch(() => {});
  },

  // ========================================================
  // FILTERS
  // ========================================================
  setCategory: (category) => {
    set((state) => ({
      filters: { ...state.filters, category },
      items: [],
      cursor: null,
      hasMore: true,
    }));
    // Re-fetch with new filter
    get().fetchInbox();
  },

  setReadFilter: (is_read) => {
    set((state) => ({
      filters: { ...state.filters, is_read },
      items: [],
      cursor: null,
      hasMore: true,
    }));
    get().fetchInbox();
  },

  // ========================================================
  // UTILITIES
  // ========================================================
  clearError: () => set({ error: null }),

  reset: () =>
    set({
      items: [],
      stats: null,
      cursor: null,
      hasMore: true,
      total: 0,
      isLoading: false,
      isRefreshing: false,
      isLoadingMore: false,
      error: null,
      unreadCount: 0,
      filters: { category: "all", is_read: null },
    }),
}));
