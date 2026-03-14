/**
 * LAYERS - Artifact Type Definitions
 * ====================================
 * FILE: mobile/src/types/artifact.ts
 *
 * Shared types for artifacts throughout the mobile app.
 * These match exactly with backend schemas (Week 3 Day 2).
 *
 * WHY THIS FILE:
 *   React Native + TypeScript needs shared type definitions
 *   so every component, screen, and service speaks the same language.
 *   These types mirror the backend Pydantic schemas 1:1.
 */

// ============================================================
// ENUMS - Match backend exactly
// ============================================================

export enum ContentType {
  LETTER = "LETTER",
  VOICE = "VOICE",
  PHOTO = "PHOTO",
  PAPER_PLANE = "PAPER_PLANE",
  VOUCHER = "VOUCHER",
  TIME_CAPSULE = "TIME_CAPSULE",
  NOTEBOOK = "NOTEBOOK",
}

export enum Visibility {
  PUBLIC = "PUBLIC",
  TARGETED = "TARGETED",
  PASSCODE = "PASSCODE",
}

export enum Layer {
  LIGHT = "LIGHT",
  SHADOW = "SHADOW",
  BOTH = "BOTH",
}

// ============================================================
// ARTIFACT MARKER - What appears on the map (preview only)
// ============================================================

export interface ArtifactMarker {
  id: string;
  latitude: number;
  longitude: number;
  content_type: ContentType;
  layer: Layer;
  visibility: Visibility;
  distance_meters: number; // Distance from user
  is_within_range: boolean; // Within 50m unlock radius
  is_unlocked: boolean; // User has opened it before
  created_at: string;
  // Preview info (no full content until unlocked)
  preview: {
    emoji: string;
    label: string;
    creator_username?: string;
    reply_count: number;
  };
}

// ============================================================
// ARTIFACT DETAIL - Full content after unlock
// ============================================================

export interface ArtifactDetail {
  id: string;
  location_id: string;
  user_id: string;
  content_type: ContentType;
  payload: Record<string, any>; // JSONB content
  visibility: Visibility;
  layer: Layer;
  created_at: string;
  updated_at: string;
  unlock_at?: string; // For TIME_CAPSULE
  expires_at?: string; // For VOUCHER
  reply_count: number;
  is_collected: boolean;
  creator: {
    username: string;
    display_name?: string;
    level: number;
  };
}

// ============================================================
// CREATE ARTIFACT - Request body
// ============================================================

export interface CreateArtifactRequest {
  latitude: number;
  longitude: number;
  content_type: ContentType;
  payload: Record<string, any>;
  visibility: Visibility;
  layer: Layer;
  target_username?: string; // For TARGETED visibility
  passcode?: string; // For PASSCODE visibility
  unlock_conditions?: Record<string, any>;
}

// ============================================================
// NEARBY RESPONSE - Paginated list from API
// ============================================================

export interface NearbyArtifactsResponse {
  artifacts: ArtifactMarker[];
  total: number;
  radius_meters: number;
  center: {
    latitude: number;
    longitude: number;
  };
}

// ============================================================
// MARKER CONFIG - Visual config per content type
// ============================================================

export interface MarkerConfig {
  emoji: string;
  lightEmoji: string;
  shadowEmoji: string;
  label: string;
  color: string;
  shadowColor: string;
  description: string;
}

/**
 * Visual config for each artifact type on the map.
 * Light vs Shadow mode shows different emojis/colors.
 */
export const MARKER_CONFIGS: Record<ContentType, MarkerConfig> = {
  [ContentType.LETTER]: {
    emoji: "💌",
    lightEmoji: "💌",
    shadowEmoji: "📜",
    label: "Letter",
    color: "#F472B6", // Pink
    shadowColor: "#A78BFA", // Purple
    description: "Someone left a message here",
  },
  [ContentType.VOICE]: {
    emoji: "🎙️",
    lightEmoji: "🎙️",
    shadowEmoji: "👻",
    label: "Voice",
    color: "#60A5FA", // Blue
    shadowColor: "#818CF8", // Indigo
    description: "A voice echoes from this spot",
  },
  [ContentType.PHOTO]: {
    emoji: "📸",
    lightEmoji: "📸",
    shadowEmoji: "🖼️",
    label: "Photo",
    color: "#34D399", // Green
    shadowColor: "#6EE7B7", // Emerald
    description: "A moment captured here",
  },
  [ContentType.PAPER_PLANE]: {
    emoji: "✈️",
    lightEmoji: "✈️",
    shadowEmoji: "🦇",
    label: "Paper Plane",
    color: "#FBBF24", // Yellow
    shadowColor: "#F59E0B", // Amber
    description: "A message flew in from afar",
  },
  [ContentType.VOUCHER]: {
    emoji: "🎁",
    lightEmoji: "🎁",
    shadowEmoji: "💀",
    label: "Voucher",
    color: "#F97316", // Orange
    shadowColor: "#EF4444", // Red
    description: "A reward waits for you",
  },
  [ContentType.TIME_CAPSULE]: {
    emoji: "⏰",
    lightEmoji: "⏰",
    shadowEmoji: "🕰️",
    label: "Time Capsule",
    color: "#8B5CF6", // Violet
    shadowColor: "#7C3AED", // Purple
    description: "A message from another time",
  },
  [ContentType.NOTEBOOK]: {
    emoji: "📓",
    lightEmoji: "📓",
    shadowEmoji: "📕",
    label: "Notebook",
    color: "#14B8A6", // Teal
    shadowColor: "#06B6D4", // Cyan
    description: "Collaborative notes at this spot",
  },
};
