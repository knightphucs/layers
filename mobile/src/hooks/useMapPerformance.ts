/**
 * LAYERS - useMapPerformance Hook
 * ====================================
 * Wraps all the "fetch on region change" logic with performance guards:
 *   - Debounced artifact fetch (300ms after pan stops)
 *   - Throttled fog fetch (2s minimum between calls)
 *   - Region change threshold (skip if <110m movement)
 *   - Cleanup on unmount (cancel pending timers)
 *
 * Without this:
 *   User pans map → 20 API calls fire → UI stutters → battery drain
 *
 * With this:
 *   User pans map → waits 300ms → 1 debounced call → smooth 60fps
 */

import { useRef, useCallback, useEffect } from "react";
import { Region } from "react-native-maps";
import { debounce, throttle, hasRegionChanged } from "../utils/performance";

interface MapPerformanceOptions {
  /** Fetch nearby artifacts (debounced) */
  onFetchArtifacts: (
    lat: number,
    lng: number,
    radius: number,
    layer?: string,
  ) => void;
  /** Fetch fog chunks (throttled) */
  onFetchFog: (region: Region) => void;
  /** Current layer filter */
  layer: string;
  /** Nearby search radius in meters */
  radius?: number;
}

export function useMapPerformance({
  onFetchArtifacts,
  onFetchFog,
  layer,
  radius = 1000,
}: MapPerformanceOptions) {
  const lastFetchCenter = useRef<{
    latitude: number;
    longitude: number;
  } | null>(null);

  // Debounced artifact fetch: wait 300ms after pan stops
  const debouncedFetchArtifacts = useRef(
    debounce((lat: number, lng: number, r: number, l: string) => {
      onFetchArtifacts(lat, lng, r, l);
    }, 300),
  ).current;

  // Throttled fog fetch: max once per 2 seconds
  const throttledFetchFog = useRef(
    throttle((region: Region) => {
      onFetchFog(region);
    }, 2000),
  ).current;

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      debouncedFetchArtifacts.cancel();
      throttledFetchFog.cancel();
    };
  }, []);

  /**
   * Called from MapView onRegionChangeComplete.
   * Decides whether to fetch based on movement threshold.
   */
  const handleRegionChange = useCallback(
    (region: Region) => {
      const center = { latitude: region.latitude, longitude: region.longitude };

      // Only fetch if moved significantly (>110m)
      if (hasRegionChanged(lastFetchCenter.current, center, 0.001)) {
        lastFetchCenter.current = center;

        // Debounced artifact fetch
        debouncedFetchArtifacts(
          region.latitude,
          region.longitude,
          radius,
          layer,
        );

        // Throttled fog fetch
        throttledFetchFog(region);
      }
    },
    [layer, radius],
  );

  /**
   * Force immediate refetch (e.g., after creating artifact, changing layer).
   */
  const forceRefetch = useCallback(
    (lat: number, lng: number) => {
      debouncedFetchArtifacts.cancel();
      onFetchArtifacts(lat, lng, radius, layer);

      if (lastFetchCenter.current) {
        onFetchFog({
          latitude: lat,
          longitude: lng,
          latitudeDelta: 0.01,
          longitudeDelta: 0.01,
        });
      }
    },
    [layer, radius, onFetchArtifacts, onFetchFog],
  );

  return {
    handleRegionChange,
    forceRefetch,
  };
}
