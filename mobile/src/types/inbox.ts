/**
 * LAYERS — Inbox Types (Week 5 Day 1)
 * ==========================================
 * Types for the Memory Inbox system.
 *
 * These EXTEND the existing types in types/index.ts.
 * Import alongside existing types:
 *   import { Artifact } from "../types";
 *   import { InboxItem, InboxReply } from "../types/inbox";
 */

import { Artifact, User } from "../types";

// ============ INBOX ITEM ============
// An artifact that was sent TO the current user,
// or a public artifact the user has interacted with.

export type InboxCategory =
  | "received"
  | "replies"
  | "paper_planes"
  | "time_capsules";

export interface InboxItem {
  id: string;
  artifact: Artifact;
  sender?: Pick<User, "id" | "username" | "avatar_url">;

  is_read: boolean;
  received_at: string;
  read_at: string | null;

  reply?: InboxReply;
}

export interface InboxReply {
  id: string;
  artifact_id: string;
  content: string;
  is_delivered: boolean;
  deliver_at: string;
  created_at: string;
  sender_username: string | null;
}

// ============ INBOX API RESPONSES ============

export interface InboxResponse {
  items: InboxItem[];
  total: number;
  unread_count: number;
  cursor: string | null;
}

export interface InboxStatsResponse {
  total_received: number;
  unread_count: number;
  replies_pending: number;
  paper_planes_found: number;
  time_capsules_waiting: number;
}

// ============ INBOX FILTERS ============

export interface InboxFilters {
  category: InboxCategory | "all";
  is_read: boolean | null;
}

// ============ UPDATED NAVIGATION ============
// Add to your existing MainTabParamList

export type UpdatedMainTabParamList = {
  Map: undefined;
  Inbox: undefined;
  Explore: undefined;
  Profile: undefined;
};
