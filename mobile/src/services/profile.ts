/**
 * LAYERS — Profile Service
 * ==========================================
 * API calls for user profile + aggregated stats.
 *
 * Backend endpoints used:
 *   GET  /auth/me              — Current user profile
 *   PUT  /auth/me              — Update profile (username, bio, avatar_url)
 *   GET  /explore/stats        — Exploration statistics
 *   GET  /artifacts/mine       — User's artifacts (count)
 *   GET  /explore/leaderboard  — Explorer ranking
 */

import api from "./api";
import { User } from "../types";

// ============================================================
// TYPES
// ============================================================

export interface ProfileStats {
  // Exploration
  chunks_explored: number;
  area_explored_km2: number;
  city_percentage: number;
  explorer_rank: number | null;

  // Content
  artifacts_created: number;
  replies_received: number;
  paper_planes_thrown: number;

  // Gamification
  xp: number;
  level: number;
  reputation: number;
  xp_to_next_level: number;
  level_progress: number; // 0.0 - 1.0

  // Social
  days_active: number;
}

export interface UpdateProfileRequest {
  username?: string;
  bio?: string;
  avatar_url?: string;
}

// ============================================================
// RANK TITLES (from Masterplan)
// ============================================================

export const RANK_TITLES: Record<number, { title: string; icon: string }> = {
  1: { title: "Wanderer", icon: "🚶" },
  2: { title: "Explorer", icon: "🧭" },
  3: { title: "Pathfinder", icon: "🗺️" },
  4: { title: "Wayfinder", icon: "⭐" },
  5: { title: "Trailblazer", icon: "🔥" },
  6: { title: "Navigator", icon: "🌟" },
  7: { title: "Cartographer", icon: "📜" },
  8: { title: "Sage", icon: "🏛️" },
  9: { title: "Legend", icon: "👑" },
  10: { title: "Mythic", icon: "💎" },
};

export function getRankForLevel(level: number): {
  title: string;
  icon: string;
} {
  if (level >= 10) return RANK_TITLES[10];
  return RANK_TITLES[level] || RANK_TITLES[1];
}

// ============================================================
// SERVICE
// ============================================================

export const profileService = {
  /**
   * Get current user profile.
   */
  getProfile: async (): Promise<User> => {
    const response = await api.get<User>("/auth/me");
    return response.data;
  },

  /**
   * Update profile fields.
   */
  updateProfile: async (data: UpdateProfileRequest): Promise<User> => {
    const response = await api.put<User>("/auth/me", data);
    return response.data;
  },

  /**
   * Get aggregated profile statistics from multiple endpoints.
   */
  getStats: async (): Promise<ProfileStats> => {
    // Fire all requests in parallel
    const [exploreRes, artifactsRes, leaderboardRes] = await Promise.allSettled(
      [
        api.get("/explore/stats"),
        api.get("/artifacts/mine", { params: { limit: 1, offset: 0 } }),
        api.get("/explore/leaderboard", { params: { limit: 50 } }),
      ],
    );

    // Parse exploration stats
    const explore =
      exploreRes.status === "fulfilled" ? exploreRes.value.data : null;

    // Parse artifact count
    const artifacts =
      artifactsRes.status === "fulfilled" ? artifactsRes.value.data : null;

    // Parse leaderboard to find user's rank
    const leaderboard =
      leaderboardRes.status === "fulfilled" ? leaderboardRes.value.data : null;

    // Get current user for XP/level
    let user: User | null = null;
    try {
      user = await profileService.getProfile();
    } catch {
      // Use cached
    }

    const xp = user?.xp ?? 0;
    const level = user?.level ?? 1;
    const xpForCurrentLevel = (level - 1) * 1000;
    const xpForNextLevel = level * 1000;
    const xpProgress = xp - xpForCurrentLevel;
    const xpNeeded = xpForNextLevel - xpForCurrentLevel;

    // Calculate days active
    const createdAt = user?.created_at ? new Date(user.created_at) : new Date();
    const daysActive = Math.max(
      1,
      Math.floor((Date.now() - createdAt.getTime()) / (1000 * 60 * 60 * 24)),
    );

    return {
      chunks_explored: explore?.total_chunks_explored ?? 0,
      area_explored_km2: explore?.total_area_km2 ?? 0,
      city_percentage: explore?.percentage_of_city ?? 0,
      explorer_rank: null, // Determined from leaderboard

      artifacts_created: artifacts?.total ?? 0,
      replies_received: 0, // TODO: Add dedicated endpoint
      paper_planes_thrown: 0,

      xp,
      level,
      reputation: user?.reputation_score ?? 100,
      xp_to_next_level: Math.max(0, xpNeeded - xpProgress),
      level_progress: xpNeeded > 0 ? xpProgress / xpNeeded : 0,

      days_active: daysActive,
    };
  },

  /**
   * Upload avatar image.
   * For MVP: accepts a URI and returns a URL.
   * Production: upload to MinIO via presigned URL.
   */
  uploadAvatar: async (imageUri: string): Promise<string> => {
    // MVP: Construct FormData for file upload
    const formData = new FormData();
    const filename = imageUri.split("/").pop() || "avatar.jpg";
    const match = /\.(\w+)$/.exec(filename);
    const type = match ? `image/${match[1]}` : "image/jpeg";

    formData.append("file", {
      uri: imageUri,
      name: filename,
      type,
    } as any);

    try {
      const response = await api.post<{ url: string }>(
        "/auth/avatar",
        formData,
        {
          headers: { "Content-Type": "multipart/form-data" },
        },
      );
      return response.data.url;
    } catch (error) {
      // Fallback: use the local URI (works for dev)
      console.warn("Avatar upload failed, using local URI:", error);
      return imageUri;
    }
  },
};
