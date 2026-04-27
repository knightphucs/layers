/**
 * LAYERS — Connection Types
 * ==========================================
 * Types for the Progressive Connection System.
 *
 * LEVELS:
 *   STRANGER  (Level 0) — Anonymous, <5 interactions
 *   SIGNAL    (Level 1) — 5+ interactions, identity revealed
 *   CONNECTED (Level 2) — Both accepted, realtime chat unlocked
 */

// ============================================================
// CORE TYPES
// ============================================================

export type ConnectionLevel = "STRANGER" | "SIGNAL" | "CONNECTED";

export interface OtherUserMini {
  id: string;
  username: string | null; // Hidden at STRANGER level
  avatar_url: string | null;
  level: number | null; // Their XP level
}

export interface ConnectionItem {
  id: string;
  other_user: OtherUserMini;
  interaction_count: number;
  level: ConnectionLevel;
  status: "PENDING" | "CONNECTED";
  can_upgrade: boolean;
  upgrade_requested_by_me: boolean;
  upgrade_requested_by_them: boolean;
  created_at: string;
  connected_at: string | null;
  last_interaction_at: string | null;
}

// ============================================================
// API RESPONSES
// ============================================================

export interface ConnectionListResponse {
  connections: ConnectionItem[];
  total: number;
  strangers_count: number;
  signals_count: number;
  connected_count: number;
}

export interface ConnectionStatsResponse {
  total_connections: number;
  strangers: number;
  signals: number;
  connected: number;
  pending_requests_received: number;
  pending_requests_sent: number;
}

export interface UpgradeResponse {
  connection_id: string;
  status: string;
  upgraded: boolean;
  message: string;
}

// ============================================================
// LEVEL DISPLAY CONFIG
// ============================================================

export const LEVEL_CONFIG: Record<
  ConnectionLevel,
  { label: string; icon: string; color: string; description: string }
> = {
  STRANGER: {
    label: "Stranger",
    icon: "👤",
    color: "#9CA3AF",
    description: "Anonymous — exchange more letters to reveal identity",
  },
  SIGNAL: {
    label: "Signal",
    icon: "📡",
    color: "#F59E0B",
    description: "You've exchanged 5+ letters — tap to request connection",
  },
  CONNECTED: {
    label: "Connected",
    icon: "✨",
    color: "#10B981",
    description: "Realtime chat unlocked",
  },
};

export const SIGNAL_THRESHOLD = 5;
