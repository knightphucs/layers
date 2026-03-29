/**
 * LAYERS — Notification Types
 * ==========================================
 * Type definitions for the push notification system.
 *
 * NOTIFICATION CATEGORIES:
 *   social    → new_reply, connection_request, connection_accepted
 *   discovery → artifact_nearby, new_artifact_in_area
 *   inbox     → slow_mail_delivered, paper_plane_landed
 *   capsule   → time_capsule_opened, time_capsule_reminder
 *   system    → welcome, level_up, badge_earned, weekly_digest
 */

// ============================================================
// NOTIFICATION TYPE ENUM
// ============================================================

export type NotificationType =
  // Social
  | "new_reply"
  | "connection_request"
  | "connection_accepted"
  // Discovery
  | "artifact_nearby"
  | "new_artifact_in_area"
  // Inbox / Slow Mail
  | "slow_mail_delivered"
  | "paper_plane_landed"
  // Time Capsule
  | "time_capsule_opened"
  | "time_capsule_reminder"
  // System / Gamification
  | "welcome"
  | "level_up"
  | "badge_earned"
  | "daily_missions_available"
  | "weekly_digest";

export type NotificationCategory =
  | "social"
  | "discovery"
  | "inbox"
  | "capsule"
  | "system";

// ============================================================
// NOTIFICATION DATA (payload sent with push)
// ============================================================

export interface NotificationData {
  type: NotificationType;
  category: NotificationCategory;

  // Deep link target
  screen?: string; // e.g. "Inbox", "Map", "ArtifactDetail"
  params?: Record<string, string>; // e.g. { artifactId: "uuid" }

  // Display
  title: string;
  body: string;
  icon?: string; // emoji

  // Metadata
  artifact_id?: string;
  sender_id?: string;
  sender_username?: string;
}

// ============================================================
// NOTIFICATION PREFERENCES
// ============================================================

export interface NotificationPreferences {
  // Master toggle
  enabled: boolean;

  // Category toggles
  social: boolean;
  discovery: boolean;
  inbox: boolean;
  capsule: boolean;
  system: boolean;

  // Quiet hours
  quiet_hours_enabled: boolean;
  quiet_hours_start: string; // "23:00"
  quiet_hours_end: string; // "07:00"
}

export const DEFAULT_NOTIFICATION_PREFERENCES: NotificationPreferences = {
  enabled: true,
  social: true,
  discovery: true,
  inbox: true,
  capsule: true,
  system: true,
  quiet_hours_enabled: true,
  quiet_hours_start: "23:00",
  quiet_hours_end: "07:00",
};

// ============================================================
// DEVICE TOKEN REGISTRATION
// ============================================================

export interface DeviceTokenRequest {
  token: string;
  platform: "ios" | "android" | "web";
  device_name?: string;
}

// ============================================================
// NOTIFICATION DISPLAY CONFIG
// ============================================================

export const NOTIFICATION_CONFIG: Record<
  NotificationType,
  { icon: string; color: string; category: NotificationCategory }
> = {
  // Social
  new_reply: { icon: "💬", color: "#6366F1", category: "social" },
  connection_request: { icon: "🤝", color: "#EC4899", category: "social" },
  connection_accepted: { icon: "✨", color: "#10B981", category: "social" },
  // Discovery
  artifact_nearby: { icon: "📍", color: "#F59E0B", category: "discovery" },
  new_artifact_in_area: { icon: "🆕", color: "#3B82F6", category: "discovery" },
  // Inbox
  slow_mail_delivered: { icon: "✉️", color: "#8B5CF6", category: "inbox" },
  paper_plane_landed: { icon: "✈️", color: "#06B6D4", category: "inbox" },
  // Capsule
  time_capsule_opened: { icon: "⏰", color: "#F97316", category: "capsule" },
  time_capsule_reminder: { icon: "🔔", color: "#EAB308", category: "capsule" },
  // System
  welcome: { icon: "🌆", color: "#6366F1", category: "system" },
  level_up: { icon: "🏆", color: "#F59E0B", category: "system" },
  badge_earned: { icon: "🎖️", color: "#10B981", category: "system" },
  daily_missions_available: {
    icon: "🎯",
    color: "#EF4444",
    category: "system",
  },
  weekly_digest: { icon: "📊", color: "#8B5CF6", category: "system" },
};
