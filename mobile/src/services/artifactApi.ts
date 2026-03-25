/**
 * LAYERS - Artifact API Service
 * ====================================
 * FILE: mobile/src/services/artifactApi.ts
 *
 * Connects the mobile app to backend artifact endpoints (Week 3 Day 2).
 * Uses the same apiClient from Week 2 (Axios instance with JWT).
 *
 * ENDPOINTS USED:
 *   GET  /artifacts/nearby?lat=X&lng=Y&radius=Z  → Map markers
 *   GET  /artifacts/:id                           → Full detail (after unlock)
 *   POST /artifacts                               → Create new artifact
 *   POST /artifacts/:id/unlock                    → Unlock with passcode
 *   POST /artifacts/:id/collect                   → Add to inventory
 *
 * PATTERN: Same as authApi.ts from Week 2 — static methods, try/catch, typed responses.
 */

import apiClient from "./api";
import {
  ArtifactMarker,
  ArtifactDetail,
  CreateArtifactRequest,
  NearbyArtifactsResponse,
  ContentType,
  Layer,
  Visibility,
  MARKER_CONFIGS,
} from "../types/artifact";

// ============================================================
// RESPONSE TYPES
// ============================================================

interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
}

// ============================================================
// ARTIFACT API SERVICE
// ============================================================

const ArtifactApi = {
  /**
   * Get nearby artifacts for map markers.
   * Called when map region changes or user moves.
   *
   * Backend: GET /api/v1/artifacts/nearby
   * Uses PostGIS ST_DWithin for fast geo-queries.
   */
  getNearby: async (
    latitude: number,
    longitude: number,
    radius: number = 1000,
    layer?: string,
    contentType?: string,
    limit: number = 50,
    offset: number = 0,
  ): Promise<ApiResponse<NearbyArtifactsResponse>> => {
    try {
      const params: Record<string, any> = {
        lat: latitude,
        lng: longitude,
        radius,
        limit,
        offset,
      };
      if (layer) params.layer = layer;
      if (contentType) params.content_type = contentType;

      const response = await apiClient.get("/artifacts/nearby", { params });
      const raw = response.data;

      // Map backend ArtifactPreview (items) → frontend ArtifactMarker (artifacts)
      const artifacts: ArtifactMarker[] = (raw.items ?? []).map((item: any) => {
        const config = MARKER_CONFIGS[item.content_type as ContentType];
        const isShadow = item.layer === Layer.SHADOW;
        return {
          id: item.id,
          latitude: item.latitude,
          longitude: item.longitude,
          content_type: item.content_type,
          layer: item.layer,
          visibility: item.visibility ?? Visibility.PUBLIC,
          distance_meters: item.distance_meters ?? 0,
          is_within_range: !item.is_locked,
          is_unlocked: item.is_unlocked ?? false,
          created_at: item.created_at ?? new Date().toISOString(),
          preview: {
            emoji: isShadow ? config?.shadowEmoji ?? "👻" : config?.lightEmoji ?? "💌",
            label: config?.label ?? item.content_type,
            creator_username: item.creator_username ?? undefined,
            reply_count: item.reply_count ?? 0,
          },
        };
      });

      return {
        success: true,
        data: {
          artifacts,
          total: raw.total,
          radius_meters: raw.radius_meters ?? radius,
          center: { latitude, longitude },
        },
      };
    } catch (error: any) {
      return {
        success: false,
        error:
          error.response?.data?.detail || "Failed to load nearby artifacts",
      };
    }
  },

  /**
   * Get full artifact detail (after user is within 50m).
   * Backend validates Proof of Presence before returning content.
   *
   * Backend: GET /api/v1/artifacts/:id?lat=X&lng=Y
   */
  getDetail: async (
    artifactId: string,
    latitude?: number,
    longitude?: number,
  ): Promise<ApiResponse<ArtifactDetail>> => {
    try {
      const params: Record<string, number> = {};
      if (typeof latitude === "number") params.lat = latitude;
      if (typeof longitude === "number") params.lng = longitude;

      const response = await apiClient.get(`/artifacts/${artifactId}`, {
        params,
      });
      return { success: true, data: response.data };
    } catch (error: any) {
      const status = error.response?.status;
      const detail = error.response?.data?.detail;
      let errorMsg =
        typeof detail === "string" ? detail : "Failed to load artifact";

      if (
        status === 403 &&
        typeof detail === "string" &&
        detail.toLowerCase().includes("someone else")
      ) {
        errorMsg = "This artifact is for someone else";
      } else if (status === 403) {
        errorMsg = "You must be within 50m to open this artifact 🔒";
      } else if (status === 404) {
        errorMsg = "This artifact no longer exists";
      } else if (status === 423) {
        // Locked — TIME_CAPSULE not yet unlockable
        errorMsg = "This time capsule isn't ready to open yet ⏰";
      }

      return { success: false, error: errorMsg };
    }
  },

  /**
   * Create a new artifact at current location.
   *
   * Backend: POST /api/v1/artifacts
   */
  create: async (
    data: CreateArtifactRequest,
  ): Promise<ApiResponse<ArtifactDetail>> => {
    try {
      const response = await apiClient.post("/artifacts", data);
      return { success: true, data: response.data };
    } catch (error: any) {
      const status = error.response?.status;
      let errorMsg = "Failed to create artifact";

      if (status === 429) {
        errorMsg = "Daily limit reached. Try again tomorrow! 🌅";
      } else if (status === 403) {
        errorMsg = "Anti-cheat: Location could not be verified";
      }

      return { success: false, error: errorMsg };
    }
  },

  /**
   * Unlock a PASSCODE-protected artifact.
   *
   * Backend: POST /api/v1/artifacts/:id/unlock
   */
  unlock: async (
    artifactId: string,
    passcode: string,
    latitude: number,
    longitude: number,
  ): Promise<ApiResponse<ArtifactDetail>> => {
    try {
      const response = await apiClient.post(
        `/artifacts/${artifactId}/unlock`,
        null,
        {
          params: {
            passcode,
            lat: latitude,
            lng: longitude,
          },
        },
      );
      return { success: true, data: response.data };
    } catch (error: any) {
      const status = error.response?.status;
      let errorMsg = "Failed to unlock";

      if (status === 401) {
        errorMsg = "Wrong passcode. Try again! 🔑";
      } else if (status === 403) {
        errorMsg = "Must be within 50m to unlock 🔒";
      }

      return { success: false, error: errorMsg };
    }
  },

  /**
   * Reply to an artifact via Slow Mail.
   *
   * Backend: POST /api/v1/artifacts/:id/reply?lat=X&lng=Y
   */
  reply: async (
    artifactId: string,
    content: string,
    latitude: number,
    longitude: number,
  ): Promise<ApiResponse<Record<string, any>>> => {
    try {
      const response = await apiClient.post(
        `/artifacts/${artifactId}/reply`,
        { content },
        {
          params: {
            lat: latitude,
            lng: longitude,
          },
        },
      );
      return { success: true, data: response.data };
    } catch (error: any) {
      return {
        success: false,
        error: error.response?.data?.detail || "Failed to send reply",
      };
    }
  },

  /**
   * Collect artifact into user's inventory.
   *
   * Backend: POST /api/v1/artifacts/:id/collect
   */
  collect: async (
    artifactId: string,
  ): Promise<ApiResponse<{ collected: boolean }>> => {
    try {
      const response = await apiClient.post(`/artifacts/${artifactId}/collect`);
      return { success: true, data: response.data };
    } catch (error: any) {
      return {
        success: false,
        error: error.response?.data?.detail || "Failed to collect",
      };
    }
  },
};

export default ArtifactApi;
