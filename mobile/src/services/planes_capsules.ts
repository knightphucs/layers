/**
 * LAYERS — Paper Planes & Capsules Service
 * ==========================================
 * API calls for Paper Planes and Time Capsules.
 *
 * Backend endpoints:
 *   POST /artifacts/paper-plane    — Throw a plane (lands 200m-1km away)
 *   POST /artifacts/time-capsule   — Create capsule with unlock_date
 *   GET  /artifacts/mine           — Filter by content_type for my capsules
 */

import api from "./api";
import {
  PaperPlaneCreateRequest,
  PaperPlaneResponse,
  TimeCapsuleCreateRequest,
  TimeCapsuleResponse,
} from "../types/planes_capsules";

// ============================================================
// PAPER PLANE SERVICE
// ============================================================

export const paperPlaneService = {
  /**
   * Throw a paper plane. Backend picks a random landing spot
   * 200m-1km from your current location.
   */
  throwPlane: async (
    data: PaperPlaneCreateRequest,
  ): Promise<PaperPlaneResponse> => {
    const response = await api.post<PaperPlaneResponse>(
      "/artifacts/paper-plane",
      data,
    );
    return response.data;
  },
};

// ============================================================
// TIME CAPSULE SERVICE
// ============================================================

export const timeCapsuleService = {
  /**
   * Create a time capsule that unlocks on a specific date.
   */
  createCapsule: async (
    data: TimeCapsuleCreateRequest,
  ): Promise<TimeCapsuleResponse> => {
    const response = await api.post<TimeCapsuleResponse>(
      "/artifacts/time-capsule",
      data,
    );
    return response.data;
  },

  /**
   * Get all time capsules created by current user.
   * Uses the existing GET /artifacts/mine endpoint,
   * then filters by content_type client-side.
   */
  getMyCapsules: async (): Promise<{
    capsules: Array<{
      id: string;
      payload: { text?: string };
      unlock_at: string | null;
      created_at: string;
      status: string;
      latitude: number;
      longitude: number;
    }>;
    locked_count: number;
    unlocked_count: number;
  }> => {
    const response = await api.get<{
      items: any[];
      total: number;
    }>("/artifacts/mine", { params: { limit: 100, offset: 0 } });

    const allArtifacts = response.data.items || [];
    const capsules = allArtifacts.filter(
      (a: any) => a.content_type === "TIME_CAPSULE",
    );

    const now = new Date();
    let locked = 0;
    let unlocked = 0;

    capsules.forEach((c: any) => {
      if (c.unlock_at && new Date(c.unlock_at) > now) {
        locked++;
      } else {
        unlocked++;
      }
    });

    return {
      capsules,
      locked_count: locked,
      unlocked_count: unlocked,
    };
  },
};
