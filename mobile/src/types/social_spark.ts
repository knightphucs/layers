/**
 * LAYERS — Social Spark Types (Week 6 Day 4)
 * ============================================
 * Mirrors backend/app/schemas/social_spark.py.
 *
 *   📡 Signal Boost   — amplify an artifact
 *   👋 Anonymous Wave — ephemeral "I'm here too"
 *   ✨ Synchronicity  — two strangers, same artifact, 30 min
 */

// ============================================================
// 📡 BOOST
// ============================================================

export interface BoostResponse {
  id: string;
  artifact_id: string;
  booster_id: string;
  boost_radius_meters: number;
  created_at: string;
  expires_at: string;
}

export interface BoostQuota {
  used_today: number;
  daily_limit: number;
  remaining: number;
}

export interface BoostedArtifactItem {
  artifact_id: string;
  latitude: number;
  longitude: number;
  distance_meters: number;
  boost_expires_at: string;
}

export interface BoostedNearbyResponse {
  items: BoostedArtifactItem[];
}

// ============================================================
// 👋 WAVE
// ============================================================

export interface WaveCreateResponse {
  wave_id: string;
  expires_at: string;
  others_waving_nearby: number;
  waved_back: boolean;
}

export interface WaveNearbyResponse {
  count: number;
  radius_meters: number;
}

// ============================================================
// ✨ SYNCHRONICITY
// ============================================================

export interface SynchronicityMatch {
  event_id: string;
  artifact_id: string;
  created_at: string;
}

export interface DiscoverResponse {
  is_new_discovery: boolean;
  synchronicity: SynchronicityMatch | null;
  message: string | null;
}

export interface SynchronicityListItem {
  event_id: string;
  artifact_id: string;
  created_at: string;
}

export interface SynchronicityListResponse {
  items: SynchronicityListItem[];
  total: number;
}
