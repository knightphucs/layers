/**
 * LAYERS - GPS Exploration Hook (Merged Version)
 * ====================================
 *
 * Tích hợp cả 2 logic:
 * 1. Store (Day 1): Lưu trữ vào Artifact Store và fetch stats.
 * 2. Fog of War (Update): Local buffer, batch API, và trigger dọn sương mù.
 *
 * WHAT IT DOES:
 * 1. Lưu tọa độ GPS mỗi 30 giây vào cả global store & local buffer.
 * 2. Tự động flush buffer (gọi API + flush store) khi đạt 20 điểm.
 * 3. Báo cáo NEW chunk count tới fog system -> trigger xóa sương mù.
 * 4. Flush dữ liệu khi app chuyển xuống background (chống mất data).
 * 5. Load initial stats cho exploration khi mount.
 */

import { useEffect, useRef, useCallback, useState } from "react";
import { AppState, AppStateStatus } from "react-native";
import { useArtifactStore } from "../store/artifactStore";
import { exploreApi, BatchExploreResponse } from "../services/exploreApi";

// ============================================================
// CONSTANTS
// ============================================================

const BUFFER_INTERVAL_MS = 30_000; // Buffer a GPS point every 30 seconds
const BUFFER_FLUSH_SIZE = 20; // Auto-flush local buffer when reaching this size
const BUFFER_MAX_SIZE = 50; // Maximum buffer size before forced flush

// ============================================================
// TYPES
// ============================================================

interface LocationData {
  latitude: number;
  longitude: number;
  accuracy?: number;
}

interface GpsPoint {
  lat: number;
  lng: number;
  timestamp: number;
  accuracy?: number;
}

interface UseExplorationOptions {
  /** Callback when new chunks are explored (connects to useFogOfWar) */
  onNewChunks?: (count: number) => void;
}

// ============================================================
// HOOK
// ============================================================

export function useExploration(
  location: LocationData | null,
  options?: UseExplorationOptions,
) {
  // --- Store logic (Day 1) ---
  const { addGpsPoint, flushGpsBuffer, fetchExplorationStats, gpsBuffer } =
    useArtifactStore();

  // --- Fog of War logic (Update) ---
  const [isExploring, setIsExploring] = useState(false);
  const [bufferSize, setBufferSize] = useState(0);
  const [lastFlushResult, setLastFlushResult] =
    useState<BatchExploreResponse | null>(null);

  const buffer = useRef<GpsPoint[]>([]);
  const isFlushing = useRef(false);

  // Refs to handle intervals cleanly without closure traps
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const lastLocationRef = useRef<LocationData | null>(null);

  // ========================================================
  // LOAD INITIAL STATS (From Day 1)
  // ========================================================
  useEffect(() => {
    fetchExplorationStats();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ========================================================
  // FLUSH — Send buffered GPS points to backend & store
  // ========================================================
  const flush = useCallback(async () => {
    // 1. Flush store buffer (Day 1)
    flushGpsBuffer();

    // 2. Flush local api buffer (Fog of War update)
    if (buffer.current.length === 0 || isFlushing.current) return;

    isFlushing.current = true;
    const points = [...buffer.current];
    buffer.current = [];
    setBufferSize(0);

    try {
      const result = await exploreApi.sendBatch(points);
      setLastFlushResult(result);

      // Notify fog system if new chunks discovered
      if (result.new_chunks > 0 && options?.onNewChunks) {
        options.onNewChunks(result.new_chunks);
      }
    } catch (error) {
      // Put points back in buffer on failure (retry next flush)
      console.warn("[Exploration] Flush failed, re-buffering:", error);
      buffer.current = [...points, ...buffer.current].slice(0, BUFFER_MAX_SIZE);
      setBufferSize(buffer.current.length);
    } finally {
      isFlushing.current = false;
    }
  }, [flushGpsBuffer, options]);

  // ========================================================
  // BUFFER GPS — Collect points at interval
  // ========================================================
  useEffect(() => {
    if (!location) {
      setIsExploring(false);
      return;
    }

    setIsExploring(true);
    lastLocationRef.current = location;

    const recordPoint = (loc: LocationData) => {
      const now = Date.now();
      const isoString = new Date(now).toISOString();

      // 1. Push to Artifact Store (Day 1 logic)
      addGpsPoint({
        latitude: loc.latitude,
        longitude: loc.longitude,
        timestamp: isoString,
        accuracy: loc.accuracy,
      });

      // 2. Push to Local Buffer for Batching (Fog of War logic)
      const point: GpsPoint = {
        lat: loc.latitude,
        lng: loc.longitude,
        timestamp: now,
        accuracy: loc.accuracy,
      };

      buffer.current.push(point);
      setBufferSize(buffer.current.length);

      // Auto-flush when local buffer is full
      if (buffer.current.length >= BUFFER_FLUSH_SIZE) {
        flush();
      }
    };

    // Add initial point immediately
    recordPoint(location);

    // Buffer GPS point at interval
    intervalRef.current = setInterval(() => {
      const loc = lastLocationRef.current;
      if (loc) {
        recordPoint(loc);
      }
    }, BUFFER_INTERVAL_MS);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location?.latitude, location?.longitude]);

  // ========================================================
  // APP STATE — Flush when going to background
  // ========================================================
  useEffect(() => {
    const handleAppState = (nextState: AppStateStatus) => {
      if (nextState === "background" || nextState === "inactive") {
        // User leaving app — flush whatever we have in both store and local buffer
        flush();
      }
    };

    const subscription = AppState.addEventListener("change", handleAppState);
    return () => subscription.remove();
  }, [flush]);

  return {
    /** Whether GPS exploration is active */
    isExploring: isExploring || gpsBuffer.length > 0,
    /** Current number of buffered GPS points (Local API Buffer) */
    bufferSize,
    /** Current number of points in the global store (Optional - useful for UI tracking) */
    storeBufferSize: gpsBuffer.length,
    /** Last batch flush result */
    lastFlushResult,
    /** Manually trigger a flush (e.g., on screen exit) */
    flush,
  };
}
