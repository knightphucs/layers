/**
 * LAYERS — Notification Service
 * ==========================================
 * API calls for push notification system.
 *
 * Backend endpoints:
 *   POST /notifications/device-token    — Register device for push
 *   DELETE /notifications/device-token  — Unregister device
 *   GET  /notifications/preferences     — Get notification preferences
 *   PUT  /notifications/preferences     — Update preferences
 *   GET  /notifications/history         — Recent notifications
 *   POST /notifications/read            — Mark notifications as read
 *
 */

import api from "./api";
import {
  DeviceTokenRequest,
  NotificationPreferences,
  DEFAULT_NOTIFICATION_PREFERENCES,
} from "../types/notifications";

// ============================================================
// NOTIFICATION SERVICE
// ============================================================

export const notificationService = {
  /**
   * Register device token with backend for push delivery.
   * Called automatically by useNotifications hook.
   */
  registerDeviceToken: async (data: DeviceTokenRequest): Promise<void> => {
    await api.post("/notifications/device-token", data);
  },

  /**
   * Unregister device token (e.g., on logout).
   */
  unregisterDeviceToken: async (token: string): Promise<void> => {
    await api.delete("/notifications/device-token", {
      data: { token },
    });
  },

  /**
   * Get user's notification preferences.
   */
  getPreferences: async (): Promise<NotificationPreferences> => {
    try {
      const response = await api.get<NotificationPreferences>(
        "/notifications/preferences",
      );
      return response.data;
    } catch (error) {
      // Return defaults if endpoint not yet available
      console.warn(
        "Notification preferences endpoint not ready, using defaults",
      );
      return DEFAULT_NOTIFICATION_PREFERENCES;
    }
  },

  /**
   * Update notification preferences.
   */
  updatePreferences: async (
    prefs: Partial<NotificationPreferences>,
  ): Promise<NotificationPreferences> => {
    try {
      const response = await api.put<NotificationPreferences>(
        "/notifications/preferences",
        prefs,
      );
      return response.data;
    } catch (error) {
      console.warn("Failed to save preferences to backend:", error);
      throw error;
    }
  },

  /**
   * Get notification history (last N notifications).
   */
  getHistory: async (params?: {
    limit?: number;
    offset?: number;
  }): Promise<{
    notifications: Array<{
      id: string;
      type: string;
      title: string;
      body: string;
      is_read: boolean;
      created_at: string;
      data: Record<string, any>;
    }>;
    total: number;
    unread_count: number;
  }> => {
    try {
      const response = await api.get("/notifications/history", {
        params: { limit: params?.limit || 50, offset: params?.offset || 0 },
      });
      return response.data;
    } catch (error) {
      return { notifications: [], total: 0, unread_count: 0 };
    }
  },

  /**
   * Mark notifications as read.
   */
  markAsRead: async (notificationIds: string[]): Promise<void> => {
    try {
      await api.post("/notifications/read", {
        notification_ids: notificationIds,
      });
    } catch (error) {
      // Non-critical
      console.warn("Failed to mark notifications as read:", error);
    }
  },

  /**
   * Clear badge count on the app icon.
   */
  clearBadge: async (): Promise<void> => {
    try {
      await api.post("/notifications/clear-badge");
    } catch (error) {
      // Non-critical
    }
  },
};
