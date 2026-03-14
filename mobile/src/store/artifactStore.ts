/**
 * LAYERS - Artifact Store (Zustand)
 * ====================================
 * FILE: mobile/src/store/artifactStore.ts
 *
 * Global state for artifacts on the map + exploration data.
 * Uses Zustand (same pattern as authStore from Week 2).
 *
 * STATE:
 *   - nearbyArtifacts: Artifacts visible on map
 *   - selectedArtifact: Currently tapped artifact (for bottom sheet)
 *   - explorationStats: Fog of War gamification data
 *   - gpsBuffer: Buffered GPS points for batch exploration
 *
 * PATTERN: Zustand with async actions + loading states.
 * Same as authStore — no class, just a plain store with actions.
 */

import { create } from "zustand";
import ArtifactApi from "../services/artifactApi";
import ExploreApi, { ExplorationStats } from "../services/exploreApi";
import {
  ArtifactMarker,
  ArtifactDetail,
  CreateArtifactRequest,
} from "../types/artifact";

// ============================================================
// STORE TYPES
// ============================================================

interface GpsPoint {
  latitude: number;
  longitude: number;
  timestamp: string;
  accuracy?: number;
}

interface ArtifactState {
  // ---- MAP MARKERS ----
  nearbyArtifacts: ArtifactMarker[];
  isLoadingNearby: boolean;
  nearbyError: string | null;
  lastFetchCenter: { lat: number; lng: number } | null;

  // ---- SELECTED ARTIFACT ----
  selectedArtifact: ArtifactMarker | null;
  artifactDetail: ArtifactDetail | null;
  isLoadingDetail: boolean;
  detailError: string | null;

  // ---- CREATION ----
  isCreating: boolean;
  createError: string | null;

  // ---- EXPLORATION / FOG OF WAR ----
  explorationStats: ExplorationStats | null;
  gpsBuffer: GpsPoint[];
  isExploring: boolean;

  // ---- ACTIONS ----
  fetchNearby: (
    lat: number,
    lng: number,
    radius?: number,
    layer?: string,
  ) => Promise<void>;
  selectArtifact: (artifact: ArtifactMarker | null) => void;
  fetchDetail: (artifactId: string, lat: number, lng: number) => Promise<void>;
  createArtifact: (data: CreateArtifactRequest) => Promise<boolean>;
  unlockArtifact: (
    artifactId: string,
    passcode: string,
    lat: number,
    lng: number,
  ) => Promise<boolean>;
  collectArtifact: (artifactId: string) => Promise<boolean>;

  // Exploration
  addGpsPoint: (point: GpsPoint) => void;
  flushGpsBuffer: () => Promise<void>;
  fetchExplorationStats: () => Promise<void>;

  // Reset
  clearSelection: () => void;
  reset: () => void;
}

// ============================================================
// CONSTANTS
// ============================================================

const GPS_BUFFER_SIZE = 20; // Flush after 20 points
const REFETCH_DISTANCE_M = 200; // Refetch if user moved > 200m from last center

// ============================================================
// STORE
// ============================================================

export const useArtifactStore = create<ArtifactState>((set, get) => ({
  // ---- INITIAL STATE ----
  nearbyArtifacts: [],
  isLoadingNearby: false,
  nearbyError: null,
  lastFetchCenter: null,

  selectedArtifact: null,
  artifactDetail: null,
  isLoadingDetail: false,
  detailError: null,

  isCreating: false,
  createError: null,

  explorationStats: null,
  gpsBuffer: [],
  isExploring: false,

  // ============================================================
  // FETCH NEARBY ARTIFACTS (for map markers)
  // ============================================================

  fetchNearby: async (lat, lng, radius = 1000, layer) => {
    const state = get();

    // Skip if we recently fetched from a nearby position
    if (state.lastFetchCenter && state.isLoadingNearby) return;
    if (state.lastFetchCenter) {
      const dist = haversineDistance(
        state.lastFetchCenter.lat,
        state.lastFetchCenter.lng,
        lat,
        lng,
      );
      if (dist < REFETCH_DISTANCE_M && state.nearbyArtifacts.length > 0) {
        return; // Still close enough, use cached data
      }
    }

    set({ isLoadingNearby: true, nearbyError: null });

    const result = await ArtifactApi.getNearby(lat, lng, radius, layer);

    if (result.success && result.data) {
      set({
        nearbyArtifacts: result.data.artifacts,
        isLoadingNearby: false,
        lastFetchCenter: { lat, lng },
      });
    } else {
      set({
        isLoadingNearby: false,
        nearbyError: result.error || "Failed to load artifacts",
      });
    }
  },

  // ============================================================
  // SELECT / VIEW ARTIFACT
  // ============================================================

  selectArtifact: (artifact) => {
    set({
      selectedArtifact: artifact,
      artifactDetail: null,
      detailError: null,
    });
  },

  fetchDetail: async (artifactId, lat, lng) => {
    set({ isLoadingDetail: true, detailError: null });

    const result = await ArtifactApi.getDetail(artifactId, lat, lng);

    if (result.success && result.data) {
      set({
        artifactDetail: result.data,
        isLoadingDetail: false,
      });
    } else {
      set({
        isLoadingDetail: false,
        detailError: result.error || "Failed to load artifact",
      });
    }
  },

  // ============================================================
  // CREATE ARTIFACT
  // ============================================================

  createArtifact: async (data) => {
    set({ isCreating: true, createError: null });

    const result = await ArtifactApi.create(data);

    if (result.success) {
      // Invalidate nearby cache so new artifact appears
      set({
        isCreating: false,
        lastFetchCenter: null,
      });
      // Immediately refresh so the new artifact appears as a marker
      await get().fetchNearby(data.latitude, data.longitude, 1000, data.layer);
      return true;
    } else {
      set({
        isCreating: false,
        createError: result.error || "Failed to create",
      });
      return false;
    }
  },

  // ============================================================
  // UNLOCK (PASSCODE)
  // ============================================================

  unlockArtifact: async (artifactId, passcode, lat, lng) => {
    const result = await ArtifactApi.unlock(artifactId, passcode, lat, lng);
    if (result.success && result.data) {
      set({ artifactDetail: result.data });
      return true;
    }
    return false;
  },

  // ============================================================
  // COLLECT
  // ============================================================

  collectArtifact: async (artifactId) => {
    const result = await ArtifactApi.collect(artifactId);
    if (result.success) {
      // Update the artifact detail to show collected
      const detail = get().artifactDetail;
      if (detail && detail.id === artifactId) {
        set({ artifactDetail: { ...detail, is_collected: true } });
      }
      return true;
    }
    return false;
  },

  // ============================================================
  // EXPLORATION / FOG OF WAR
  // ============================================================

  addGpsPoint: (point) => {
    const buffer = [...get().gpsBuffer, point];

    if (buffer.length >= GPS_BUFFER_SIZE) {
      // Auto-flush when buffer is full
      set({ gpsBuffer: buffer });
      get().flushGpsBuffer();
    } else {
      set({ gpsBuffer: buffer });
    }
  },

  flushGpsBuffer: async () => {
    const { gpsBuffer, isExploring } = get();
    if (gpsBuffer.length === 0 || isExploring) return;

    set({ isExploring: true });

    const points = [...gpsBuffer];
    set({ gpsBuffer: [] }); // Clear immediately

    const result = await ExploreApi.sendBatch(points);

    set({ isExploring: false });

    if (result.success && result.data) {
      // Could trigger fog clear animation here
      // console.log(`Explored ${result.data.new_chunks} new chunks!`);
    }
  },

  fetchExplorationStats: async () => {
    const result = await ExploreApi.getStats();
    if (result.success && result.data) {
      set({ explorationStats: result.data });
    }
  },

  // ============================================================
  // UTILS
  // ============================================================

  clearSelection: () => {
    set({
      selectedArtifact: null,
      artifactDetail: null,
      detailError: null,
    });
  },

  reset: () => {
    set({
      nearbyArtifacts: [],
      isLoadingNearby: false,
      nearbyError: null,
      lastFetchCenter: null,
      selectedArtifact: null,
      artifactDetail: null,
      isLoadingDetail: false,
      detailError: null,
      isCreating: false,
      createError: null,
      explorationStats: null,
      gpsBuffer: [],
      isExploring: false,
    });
  },
}));

// ============================================================
// HAVERSINE DISTANCE (for cache invalidation)
// ============================================================

function haversineDistance(
  lat1: number,
  lng1: number,
  lat2: number,
  lng2: number,
): number {
  const R = 6371000; // Earth radius in meters
  const toRad = (x: number) => (x * Math.PI) / 180;

  const dLat = toRad(lat2 - lat1);
  const dLng = toRad(lng2 - lng1);

  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(toRad(lat1)) *
      Math.cos(toRad(lat2)) *
      Math.sin(dLng / 2) *
      Math.sin(dLng / 2);

  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}
