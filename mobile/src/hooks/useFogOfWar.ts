/**
 * LAYERS - useFogOfWar Hook
 * ====================================
 * FILE: mobile/src/hooks/useFogOfWar.ts
 *
 * The brain of the Fog of War system on mobile.
 * Connects: GPS location → Backend API → Fog Overlay rendering
 *
 * RESPONSIBILITIES:
 *   1. Fetch explored chunks for current viewport from backend
 *   2. Detect NEW chunks cleared (trigger animation + haptics)
 *   3. Cache explored chunks to minimize API calls
 *   4. Compute fog stats (percentage, area) for UI
 *   5. Handle viewport changes (pan/zoom = refetch)
 *
 * SMART CACHING:
 *   - Keep a local Set of explored chunk keys ("cx:cy")
 *   - Only refetch when viewport moves significantly
 *   - When batch explore returns new_chunks > 0, refetch viewport
 *
 * FLOW:
 *   MapScreen renders → region changes → useFogOfWar fetches chunks
 *   → FogOverlay renders polygon with holes
 *   → useExploration sends GPS → backend marks chunks
 *   → new chunk detected → FogClearAnimation triggers
 */

import { useState, useCallback, useRef, useEffect, useMemo } from "react";
import {
  exploreService,
  ExploredChunkData,
  ViewportChunksResponse,
} from "../services/explore";

// ============================================================
// TYPES
// ============================================================

interface MapRegion {
  latitude: number;
  longitude: number;
  latitudeDelta: number;
  longitudeDelta: number;
}

interface FogClearEvent {
  id: string;
  latitude: number;
  longitude: number;
  timestamp: number;
}

interface FogState {
  /** Explored chunks in current viewport for rendering */
  exploredChunks: ExploredChunkData[];
  /** 0-100, how much of viewport is still fogged */
  fogPercentage: number;
  /** Total chunks explored (all time) */
  totalExplored: number;
  /** Latest fog clear event for animation */
  clearEvent: FogClearEvent | null;
  /** Whether currently fetching chunks */
  isLoading: boolean;
  /** Flash indicator for new chunk */
  newChunkFlash: boolean;
}

// ============================================================
// CONSTANTS
// ============================================================

/** Minimum viewport shift (in degrees) before refetching */
const REFETCH_THRESHOLD_DEG = 0.002; // ~220m

/** Minimum time between viewport fetches (ms) */
const REFETCH_COOLDOWN_MS = 2000;

/** Radius for chunk fetch = viewport diagonal (approximate) */
function viewportToRadius(region: MapRegion): number {
  // Convert latitudeDelta to meters (rough)
  const latMeters = region.latitudeDelta * 111_000;
  const lngMeters =
    region.longitudeDelta *
    111_000 *
    Math.cos((region.latitude * Math.PI) / 180);
  // Diagonal / 2 = radius
  const diagonal = Math.sqrt(latMeters ** 2 + lngMeters ** 2);
  return Math.min(Math.round(diagonal / 2), 5000); // Max 5km
}

// ============================================================
// HOOK
// ============================================================

export function useFogOfWar() {
  // State
  const [state, setState] = useState<FogState>({
    exploredChunks: [],
    fogPercentage: 100,
    totalExplored: 0,
    clearEvent: null,
    isLoading: false,
    newChunkFlash: false,
  });

  // Refs for caching / throttling
  const lastFetchRegion = useRef<MapRegion | null>(null);
  const lastFetchTime = useRef<number>(0);
  const knownChunks = useRef<Set<string>>(new Set());
  const clearEventCounter = useRef(0);

  // ========================================================
  // FETCH CHUNKS — Called when viewport changes
  // ========================================================

  const fetchViewportChunks = useCallback(
    async (region: MapRegion, force: boolean = false) => {
      const now = Date.now();

      // Throttle: don't refetch too fast
      if (!force && now - lastFetchTime.current < REFETCH_COOLDOWN_MS) {
        return;
      }

      // Skip if viewport hasn't moved enough
      if (!force && lastFetchRegion.current) {
        const latDiff = Math.abs(
          region.latitude - lastFetchRegion.current.latitude,
        );
        const lngDiff = Math.abs(
          region.longitude - lastFetchRegion.current.longitude,
        );
        if (
          latDiff < REFETCH_THRESHOLD_DEG &&
          lngDiff < REFETCH_THRESHOLD_DEG
        ) {
          return;
        }
      }

      lastFetchRegion.current = region;
      lastFetchTime.current = now;

      try {
        setState((prev) => ({ ...prev, isLoading: true }));

        const radius = viewportToRadius(region);
        const response: ViewportChunksResponse =
          await exploreService.getViewportChunks(
            region.latitude,
            region.longitude,
            radius,
          );

        // Detect NEW chunks (not in our known set)
        let latestNew: ExploredChunkData | null = null;
        for (const chunk of response.explored) {
          const key = `${chunk.chunk_x}:${chunk.chunk_y}`;
          if (!knownChunks.current.has(key)) {
            knownChunks.current.add(key);
            latestNew = chunk; // Track the most recent new one
          }
        }

        // Build clear event if new chunk found
        let clearEvent: FogClearEvent | null = null;
        if (latestNew && latestNew.bounds && knownChunks.current.size > 1) {
          // Don't animate on initial load (size > 1 means not first fetch)
          clearEventCounter.current += 1;
          clearEvent = {
            id: `clear-${clearEventCounter.current}`,
            latitude: (latestNew.bounds.lat_min + latestNew.bounds.lat_max) / 2,
            longitude:
              (latestNew.bounds.lng_min + latestNew.bounds.lng_max) / 2,
            timestamp: now,
          };
        }

        setState((prev) => ({
          ...prev,
          exploredChunks: response.explored,
          fogPercentage: response.fog_percentage,
          totalExplored: response.explored_in_viewport,
          clearEvent: clearEvent ?? prev.clearEvent,
          newChunkFlash: !!clearEvent,
          isLoading: false,
        }));

        // Reset flash after delay
        if (clearEvent) {
          setTimeout(() => {
            setState((prev) => ({ ...prev, newChunkFlash: false }));
          }, 2000);
        }
      } catch (error) {
        console.warn("[FogOfWar] Failed to fetch chunks:", error);
        setState((prev) => ({ ...prev, isLoading: false }));
      }
    },
    [],
  );

  // ========================================================
  // ON NEW EXPLORATION — Called when useExploration flushes
  // ========================================================

  /**
   * Called after GPS buffer flush reports new chunks.
   * Forces a viewport refetch to update fog overlay.
   */
  const onNewChunksExplored = useCallback(
    (newCount: number) => {
      if (newCount > 0 && lastFetchRegion.current) {
        // Force refetch to pick up new chunks
        fetchViewportChunks(lastFetchRegion.current, true);
      }
    },
    [fetchViewportChunks],
  );

  // ========================================================
  // FETCH TOTAL STATS — For profile / gamification
  // ========================================================

  const [totalStats, setTotalStats] = useState({
    totalChunksAllTime: 0,
    totalAreaKm2: 0,
    cityPercentage: 0,
  });

  const fetchTotalStats = useCallback(async () => {
    try {
      const stats = await exploreService.getStats();
      setTotalStats({
        totalChunksAllTime: stats.total_chunks_explored ?? 0,
        totalAreaKm2: stats.total_area_km2 ?? 0,
        cityPercentage: stats.percentage_of_city ?? 0,
      });
    } catch (error) {
      console.warn("[FogOfWar] Failed to fetch stats:", error);
    }
  }, []);

  // Load stats on mount
  useEffect(() => {
    fetchTotalStats();
  }, []);

  return {
    // Fog rendering data
    exploredChunks: state.exploredChunks,
    fogPercentage: state.fogPercentage,
    clearEvent: state.clearEvent,
    newChunkFlash: state.newChunkFlash,
    isLoading: state.isLoading,

    // Total stats (all-time)
    totalStats,

    // Actions
    fetchViewportChunks,
    onNewChunksExplored,
    fetchTotalStats,
  };
}
