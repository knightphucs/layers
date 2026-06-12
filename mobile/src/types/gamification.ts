/**
 * LAYERS — Gamification Types (Week 7 Day 5)
 */

// ---- Badges ----
export interface BadgeItem {
  id: string;
  title: string;
  description: string;
  icon: string;
  unlocked: boolean;
  unlocked_at?: string | null;
}

export interface BadgesResponse {
  badges: BadgeItem[];
  unlocked_count: number;
  total: number;
}

// ---- Leaderboard ----
export type LeaderboardScope = "global" | "weekly";

export interface LeaderboardEntry {
  rank: number;
  user_id: string;
  username: string;
  avatar_url?: string | null;
  score: number;
  is_me: boolean;
}

export interface LeaderboardResponse {
  scope: string;
  entries: LeaderboardEntry[];
  my_rank?: number | null;
  my_score: number;
}
