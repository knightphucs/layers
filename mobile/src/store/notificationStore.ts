/**
 * LAYERS — Notification Store (Week 5 Day 2)
 * ==========================================
 * Zustand store for notification state.
 *
 * PATTERN: Same as authStore, inboxStore.
 *
 * Features:
 *   - Notification preferences (per-category toggles)
 *   - In-app notification list (last 50)
 *   - Badge count management
 *   - Quiet hours check
 *   - Persist preferences to AsyncStorage
 */

import { create } from "zustand";
import * as SecureStore from "expo-secure-store";
import * as Notifications from "expo-notifications";
import { notificationService } from "../services/notifications";
import {
  NotificationPreferences,
  NotificationCategory,
  NotificationType,
  DEFAULT_NOTIFICATION_PREFERENCES,
} from "../types/notifications";

// ============================================================
// IN-APP NOTIFICATION ITEM
// ============================================================

export interface InAppNotification {
  id: string;
  type: NotificationType | string;
  title: string;
  body: string;
  data?: Record<string, any>;
  received_at: string;
  is_read: boolean;
}

// ============================================================
// STATE
// ============================================================

interface NotificationState {
  // Preferences
  preferences: NotificationPreferences;

  // In-app notifications (ephemeral — not persisted across sessions)
  notifications: InAppNotification[];
  badgeCount: number;

  // Loading
  isLoading: boolean;

  // Actions — Preferences
  loadPreferences: () => Promise<void>;
  updatePreference: (key: keyof NotificationPreferences, value: any) => void;
  savePreferences: () => Promise<void>;
  toggleCategory: (category: NotificationCategory) => void;
  toggleMasterSwitch: () => void;

  // Actions — Notifications
  addNotification: (notification: InAppNotification) => void;
  markAsRead: (id: string) => void;
  markAllRead: () => void;
  clearNotifications: () => void;
  incrementBadge: () => void;
  clearBadge: () => void;

  // Helpers
  isInQuietHours: () => boolean;
  isCategoryEnabled: (category: NotificationCategory) => boolean;
}

// ============================================================
// STORE
// ============================================================

export const useNotificationStore = create<NotificationState>((set, get) => ({
  preferences: DEFAULT_NOTIFICATION_PREFERENCES,
  notifications: [],
  badgeCount: 0,
  isLoading: false,

  // ========================================================
  // LOAD PREFERENCES
  // ========================================================
  loadPreferences: async () => {
    set({ isLoading: true });
    try {
      // Try local first (faster)
      const stored = await SecureStore.getItemAsync("notification_prefs");
      if (stored) {
        set({ preferences: JSON.parse(stored) });
      }

      // Then sync with backend
      const remote = await notificationService.getPreferences();
      set({ preferences: remote });

      // Update local cache
      await SecureStore.setItemAsync(
        "notification_prefs",
        JSON.stringify(remote),
      );
    } catch (error) {
      console.warn("Failed to load notification preferences:", error);
    } finally {
      set({ isLoading: false });
    }
  },

  // ========================================================
  // UPDATE PREFERENCE
  // ========================================================
  updatePreference: (key, value) => {
    set((state) => ({
      preferences: { ...state.preferences, [key]: value },
    }));
  },

  // ========================================================
  // SAVE PREFERENCES (to backend + local)
  // ========================================================
  savePreferences: async () => {
    const { preferences } = get();
    try {
      await SecureStore.setItemAsync(
        "notification_prefs",
        JSON.stringify(preferences),
      );
      await notificationService.updatePreferences(preferences);
    } catch (error) {
      console.warn("Failed to save preferences:", error);
    }
  },

  // ========================================================
  // TOGGLE CATEGORY
  // ========================================================
  toggleCategory: (category) => {
    set((state) => {
      const newPrefs = {
        ...state.preferences,
        [category]: !state.preferences[category],
      };
      // Fire-and-forget save
      SecureStore.setItemAsync(
        "notification_prefs",
        JSON.stringify(newPrefs),
      ).catch(() => {});
      notificationService.updatePreferences(newPrefs).catch(() => {});
      return { preferences: newPrefs };
    });
  },

  // ========================================================
  // TOGGLE MASTER SWITCH
  // ========================================================
  toggleMasterSwitch: () => {
    set((state) => {
      const newEnabled = !state.preferences.enabled;
      const newPrefs = { ...state.preferences, enabled: newEnabled };
      SecureStore.setItemAsync(
        "notification_prefs",
        JSON.stringify(newPrefs),
      ).catch(() => {});
      notificationService.updatePreferences(newPrefs).catch(() => {});
      return { preferences: newPrefs };
    });
  },

  // ========================================================
  // ADD NOTIFICATION (from foreground handler)
  // ========================================================
  addNotification: (notification) => {
    set((state) => ({
      notifications: [notification, ...state.notifications].slice(0, 50),
    }));
  },

  // ========================================================
  // MARK AS READ
  // ========================================================
  markAsRead: (id) => {
    set((state) => ({
      notifications: state.notifications.map((n) =>
        n.id === id ? { ...n, is_read: true } : n,
      ),
    }));
    notificationService.markAsRead([id]).catch(() => {});
  },

  markAllRead: () => {
    const { notifications } = get();
    const unreadIds = notifications.filter((n) => !n.is_read).map((n) => n.id);
    set((state) => ({
      notifications: state.notifications.map((n) => ({
        ...n,
        is_read: true,
      })),
      badgeCount: 0,
    }));
    if (unreadIds.length > 0) {
      notificationService.markAsRead(unreadIds).catch(() => {});
    }
    Notifications.setBadgeCountAsync(0).catch(() => {});
  },

  // ========================================================
  // CLEAR
  // ========================================================
  clearNotifications: () => {
    set({ notifications: [], badgeCount: 0 });
    Notifications.setBadgeCountAsync(0).catch(() => {});
  },

  // ========================================================
  // BADGE
  // ========================================================
  incrementBadge: () => {
    set((state) => {
      const newCount = state.badgeCount + 1;
      Notifications.setBadgeCountAsync(newCount).catch(() => {});
      return { badgeCount: newCount };
    });
  },

  clearBadge: () => {
    set({ badgeCount: 0 });
    Notifications.setBadgeCountAsync(0).catch(() => {});
  },

  // ========================================================
  // HELPERS
  // ========================================================
  isInQuietHours: () => {
    const { preferences } = get();
    if (!preferences.quiet_hours_enabled) return false;

    const now = new Date();
    const currentMinutes = now.getHours() * 60 + now.getMinutes();

    const [startH, startM] = preferences.quiet_hours_start
      .split(":")
      .map(Number);
    const [endH, endM] = preferences.quiet_hours_end.split(":").map(Number);

    const startMinutes = startH * 60 + startM;
    const endMinutes = endH * 60 + endM;

    // Handle overnight quiet hours (e.g., 23:00 - 07:00)
    if (startMinutes > endMinutes) {
      return currentMinutes >= startMinutes || currentMinutes <= endMinutes;
    }

    return currentMinutes >= startMinutes && currentMinutes <= endMinutes;
  },

  isCategoryEnabled: (category) => {
    const { preferences } = get();
    if (!preferences.enabled) return false;
    return preferences[category] ?? true;
  },
}));
