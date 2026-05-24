/**
 * LAYERS — Social Spark Service
 * =============================================
 * REST helpers for boost / wave / synchronicity.
 * Object-literal pattern (same as authService, chatService).
 */

import api from "./api";
import {
  BoostResponse,
  BoostQuota,
  BoostedNearbyResponse,
  WaveCreateResponse,
  WaveNearbyResponse,
  DiscoverResponse,
  SynchronicityListResponse,
} from "../types/social_spark";

export const socialSparkService = {
  // ---- 📡 Boost ----

  boostArtifact: async (artifactId: string): Promise<BoostResponse> => {
    const response = await api.post<BoostResponse>(
      `/spark/artifacts/${artifactId}/boost`,
    );
    return response.data;
  },

  getBoostQuota: async (): Promise<BoostQuota> => {
    const response = await api.get<BoostQuota>("/spark/boosts/quota");
    return response.data;
  },

  getBoostedNearby: async (
    latitude: number,
    longitude: number,
  ): Promise<BoostedNearbyResponse> => {
    const response = await api.get<BoostedNearbyResponse>(
      "/spark/boosted-nearby",
      { params: { lat: latitude, lng: longitude } },
    );
    return response.data;
  },

  // ---- 👋 Wave ----

  wave: async (
    latitude: number,
    longitude: number,
  ): Promise<WaveCreateResponse> => {
    const response = await api.post<WaveCreateResponse>("/spark/wave", {
      latitude,
      longitude,
    });
    return response.data;
  },

  getWavesNearby: async (
    latitude: number,
    longitude: number,
    radiusMeters: number = 150,
  ): Promise<WaveNearbyResponse> => {
    const response = await api.get<WaveNearbyResponse>("/spark/waves/nearby", {
      params: { lat: latitude, lng: longitude, radius_meters: radiusMeters },
    });
    return response.data;
  },

  // ---- ✨ Synchronicity ----

  /**
   * Call the moment an artifact unlocks on the client (within 50m, content
   * revealed). Idempotent per user — safe to call every time detail opens.
   * Returns a synchronicity match if another explorer just unlocked it too.
   */
  discoverArtifact: async (
    artifactId: string,
    latitude?: number,
    longitude?: number,
  ): Promise<DiscoverResponse> => {
    const body: Record<string, number> = {};
    if (latitude != null) body.latitude = latitude;
    if (longitude != null) body.longitude = longitude;
    const response = await api.post<DiscoverResponse>(
      `/spark/artifacts/${artifactId}/discover`,
      body,
    );
    return response.data;
  },

  getSynchronicities: async (
    limit: number = 50,
    offset: number = 0,
  ): Promise<SynchronicityListResponse> => {
    const response = await api.get<SynchronicityListResponse>(
      "/spark/synchronicities",
      { params: { limit, offset } },
    );
    return response.data;
  },
};
