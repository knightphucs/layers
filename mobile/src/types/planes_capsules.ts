/**
 * LAYERS — Paper Plane & Time Capsule Types
 * ==========================================
 */

// ============================================================
// PAPER PLANES
// ============================================================

export interface PaperPlaneCreateRequest {
  text: string;
  latitude: number;
  longitude: number;
}

export interface PaperPlaneResponse {
  id: string;
  text: string;
  landed_at: {
    latitude: number;
    longitude: number;
  };
  flight_distance_meters: number;
  created_at: string;
}

// ============================================================
// TIME CAPSULES
// ============================================================

export type CapsulePreset =
  | "1_week"
  | "1_month"
  | "6_months"
  | "1_year"
  | "custom";

export interface TimeCapsulePreset {
  key: CapsulePreset;
  label: string;
  days: number;
  icon: string;
  description: string;
}

export const CAPSULE_PRESETS: TimeCapsulePreset[] = [
  {
    key: "1_week",
    label: "1 Week",
    days: 7,
    icon: "📅",
    description: "A quick reminder to future you",
  },
  {
    key: "1_month",
    label: "1 Month",
    days: 30,
    icon: "🗓️",
    description: "Check in with yourself next month",
  },
  {
    key: "6_months",
    label: "6 Months",
    days: 180,
    icon: "⏳",
    description: "Half a year away",
  },
  {
    key: "1_year",
    label: "1 Year",
    days: 365,
    icon: "🎊",
    description: "An anniversary from now",
  },
  {
    key: "custom",
    label: "Custom",
    days: 0,
    icon: "✏️",
    description: "Pick a specific date",
  },
];

export interface TimeCapsuleCreateRequest {
  text: string;
  latitude: number;
  longitude: number;
  unlock_date: string; // ISO datetime
  media_url?: string;
}

export interface TimeCapsuleResponse {
  id: string;
  content_type: "TIME_CAPSULE";
  unlock_at: string;
  created_at: string;
  message: string;
}

// ============================================================
// CAPSULE COUNTDOWN HELPER
// ============================================================

export interface CapsuleCountdown {
  days: number;
  hours: number;
  minutes: number;
  seconds: number;
  is_unlocked: boolean;
  formatted: string; // e.g. "3 months, 12 days"
}

export function calculateCountdown(unlockIso: string): CapsuleCountdown {
  const unlock = new Date(unlockIso);
  const now = new Date();
  const diffMs = unlock.getTime() - now.getTime();

  if (diffMs <= 0) {
    return {
      days: 0,
      hours: 0,
      minutes: 0,
      seconds: 0,
      is_unlocked: true,
      formatted: "Ready to open!",
    };
  }

  const totalSeconds = Math.floor(diffMs / 1000);
  const days = Math.floor(totalSeconds / 86400);
  const hours = Math.floor((totalSeconds % 86400) / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  // Human-readable formatting
  let formatted: string;
  if (days >= 30) {
    const months = Math.floor(days / 30);
    const remDays = days % 30;
    formatted =
      remDays > 0
        ? `${months} month${months > 1 ? "s" : ""}, ${remDays} day${remDays > 1 ? "s" : ""}`
        : `${months} month${months > 1 ? "s" : ""}`;
  } else if (days >= 1) {
    formatted = `${days} day${days > 1 ? "s" : ""}, ${hours}h`;
  } else if (hours >= 1) {
    formatted = `${hours}h ${minutes}m`;
  } else {
    formatted = `${minutes}m ${seconds}s`;
  }

  return { days, hours, minutes, seconds, is_unlocked: false, formatted };
}
