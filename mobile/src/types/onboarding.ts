/**
 * LAYERS — Onboarding Types
 * ==========================================
 * Types for the story-mode onboarding flow.
 *
 * FLOW:
 *   StoryIntro → LayerChoice → Permissions → FirstMission → Main app
 *
 * The flow runs ONCE per device (flag persisted via SecureStore).
 */

import { Layer } from "./index";

// ============================================================
// NAVIGATION
// ============================================================

export type OnboardingStackParamList = {
  StoryIntro: undefined;
  LayerChoice: undefined;
  Permissions: undefined;
  FirstMission: undefined;
};

// ============================================================
// STORY PAGES
// ============================================================

export interface StoryPage {
  key: string;
  emoji: string;
  title: string;
  body: string;
  /** Which theme this page previews. Drives background + accent colors. */
  theme: "light" | "shadow" | "neutral";
}

/**
 * The story-mode script — grounded in the masterplan philosophy:
 * "The city isn't flat. It's a stack of parallel worlds."
 */
export const STORY_PAGES: StoryPage[] = [
  {
    key: "city",
    emoji: "🌆",
    title: "The city isn't flat",
    body: "Beneath every street you walk lies a hidden layer of memories, secrets, and stories left by strangers.",
    theme: "neutral",
  },
  {
    key: "light",
    emoji: "☀️",
    title: "The Light Layer",
    body: "By day, the city heals. Leave letters at places you love, throw paper planes to strangers, and send messages to your future self.",
    theme: "light",
  },
  {
    key: "shadow",
    emoji: "🌙",
    title: "The Shadow Layer",
    body: "After midnight, the city changes. Glitch zones hum, urban legends surface, and some doors only open between 23:00 and 03:00.",
    theme: "shadow",
  },
  {
    key: "fog",
    emoji: "🗺️",
    title: "Your map starts dark",
    body: "LAYERS only reveals what you've truly walked. Every step lifts the fog. Your city, discovered by your own two feet.",
    theme: "neutral",
  },
];

// ============================================================
// PERMISSIONS
// ============================================================

export type PermissionKey = "location" | "notifications";

export type PermissionStatus = "unknown" | "granted" | "denied";

export interface PermissionItem {
  key: PermissionKey;
  icon: string;
  title: string;
  description: string;
  /** Location is required for the core loop; notifications are optional. */
  required: boolean;
}

export const PERMISSION_ITEMS: PermissionItem[] = [
  {
    key: "location",
    icon: "📍",
    title: "Location",
    description:
      "LAYERS is played on your real city map. We need your location to lift the fog and unlock artifacts within 50m.",
    required: true,
  },
  {
    key: "notifications",
    icon: "🔔",
    title: "Notifications",
    description:
      "Know when a Slow Mail arrives, a Paper Plane lands near you, or a Time Capsule unlocks. Optional — you choose.",
    required: false,
  },
];

// ============================================================
// FIRST MISSION
// ============================================================

export interface FirstMission {
  icon: string;
  title: string;
  description: string;
  xpReward: number;
}

export const FIRST_MISSIONS: FirstMission[] = [
  {
    icon: "🌫️",
    title: "Lift your first fog",
    description: "Open the map and take a short walk — watch the city reveal itself.",
    xpReward: 15, // XPEventType.EXPLORE_NEW_CHUNK — must match backend XP_VALUES
  },
  {
    icon: "📍",
    title: "First check-in",
    description: "Check in at the place you're standing right now.",
    xpReward: 25, // XPEventType.FIRST_CHECK_IN
  },
];

// Re-export for convenience in onboarding screens
export type { Layer };
