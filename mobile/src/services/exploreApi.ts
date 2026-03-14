/**
 * LAYERS - Explore API Service (Merged Version)
 * ==========================================
 * Tích hợp cả Day 1 (Legacy) và bản cập nhật Fog of War (Day 3).
 * Kết nối mobile app tới backend để gửi GPS trail và nhận chunks.
 *
 * ENDPOINTS:
 * POST /api/v1/explore         — Single point explore
 * POST /api/v1/explore/batch   — GPS trail buffer
 * GET  /api/v1/explore/chunks  — Viewport chunks for fog overlay
 * GET  /api/v1/explore/stats   — Gamification data
 * GET  /api/v1/explore/heatmap — Community heatmap
 */

import apiClient from "./api";

// ============================================================
// TYPES — Merged (Day 1 + Fog of War)
// ============================================================

export interface ChunkBounds {
  lat_min: number;
  lat_max: number;
  lng_min: number;
  lng_max: number;
}

/** Tích hợp: Hỗ trợ cả `bounds` (mới) và optional cho code cũ */
export interface ExploredChunkData {
  chunk_x: number;
  chunk_y: number;
  explored_at: string;
  bounds?: ChunkBounds;
}

/** Tích hợp Viewport: Gộp field của cả 2 phiên bản */
export interface ViewportChunksResponse {
  // --- Fog of War fields ---
  explored: ExploredChunkData[];
  total_in_viewport: number;
  explored_in_viewport: number;
  fog_percentage: number;

  // --- Day 1 Legacy fields ---
  chunks?: ExploredChunkData[];
  total?: number;
  viewport?: {
    min_lat: number;
    max_lat: number;
    min_lng: number;
    max_lng: number;
  };
}

export interface ExploreResponse {
  is_new: boolean;
  chunk_x: number;
  chunk_y: number;
  message: string;
  total_explored: number;
}

/** Tích hợp Batch: Giữ thêm total_chunks của Day 1 */
export interface BatchExploreResponse {
  new_chunks: number;
  points_processed: number;
  unique_chunks: number;
  total_explored: number;
  area_sqm: number;
  total_chunks?: number; // Legacy
}

/** Tích hợp Stats: Giữ lại rank từ Day 1 */
export interface ExplorationStatsResponse {
  total_chunks_explored: number;
  total_area_sqm: number;
  total_area_km2?: number;
  percentage_of_city: number;
  recent_chunks: Array<{
    chunk_x: number;
    chunk_y: number;
    explored_at: string;
  }>;
  rank?: number; // Legacy
}

export interface HeatmapCell {
  chunk_x: number;
  chunk_y: number;
  explorer_count: number;
  heat_level: "hot" | "warm" | "cool" | "cold";
  bounds: ChunkBounds;
}

/** Hỗ trợ cả format {latitude, longitude} (Day 1) và {lat, lng} (Day 3) */
export interface GpsPoint {
  latitude?: number;
  longitude?: number;
  lat?: number;
  lng?: number;
  timestamp: string | number;
  accuracy?: number;
}

// Legacy ApiResponse wrapper (Dành cho các component chưa chuyển sang try/catch)
export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
}

// ============================================================
// API SERVICE
// ============================================================

export const exploreApi = {
  /**
   * Mark a single GPS position as explored.
   */
  async exploreSingle(
    latitude: number,
    longitude: number,
  ): Promise<ExploreResponse> {
    const response = await apiClient.post("/explore", {
      latitude,
      longitude,
    });
    return response.data;
  },

  /**
   * Send buffered GPS trail for batch exploration.
   * Gộp: Xử lý mảng điểm chuẩn hóa để an toàn gửi lên backend.
   */
  async sendBatch(points: GpsPoint[]): Promise<BatchExploreResponse> {
    // Gửi cả keys cũ và mới phòng hờ backend chưa update xong model
    const response = await apiClient.post("/explore/batch", {
      points: points, // Legacy key
      coordinates: points, // New Fog of War key
    });
    return response.data;
  },

  /**
   * Get explored chunks within a viewport for fog rendering.
   * SMART OVERLOAD: Hỗ trợ cả 2 chuẩn gọi API.
   * * - Cách 1 (Day 1): getViewportChunks(minLat, maxLat, minLng, maxLng)
   * - Cách 2 (Day 3): getViewportChunks(lat, lng, radius)
   */
  async getViewportChunks(
    arg1: number,
    arg2: number,
    arg3: number = 1000,
    arg4?: number,
  ): Promise<ViewportChunksResponse> {
    if (arg4 !== undefined) {
      // Logic Legacy: Gọi theo bounding box
      const response = await apiClient.get("/explore/chunks", {
        params: { min_lat: arg1, max_lat: arg2, min_lng: arg3, max_lng: arg4 },
      });
      return response.data;
    } else {
      // Logic Fog of War: Gọi theo tâm tọa độ và bán kính
      const response = await apiClient.get("/explore/chunks", {
        params: { lat: arg1, lng: arg2, radius: arg3 },
      });
      return response.data;
    }
  },

  /**
   * Get total exploration stats for profile / gamification.
   */
  async getStats(): Promise<ExplorationStatsResponse> {
    const response = await apiClient.get("/explore/stats");
    return response.data;
  },

  /**
   * Get community heatmap for an area.
   */
  async getHeatmap(
    lat: number,
    lng: number,
    radius: number = 1000,
  ): Promise<{ cells: HeatmapCell[] }> {
    const response = await apiClient.get("/explore/heatmap", {
      params: { lat, lng, radius },
    });
    return response.data;
  },
};

// ============================================================
// BACKWARD COMPATIBILITY EXPORTS
// ============================================================

/** * Wrapper hỗ trợ các Component Day 1 vẫn đang xài cú pháp:
 * const { success, data, error } = await ExploreApi.getStats();
 */
export const ExploreApiLegacy = {
  sendBatch: async (
    points: GpsPoint[],
  ): Promise<ApiResponse<BatchExploreResponse>> => {
    try {
      const data = await exploreApi.sendBatch(points);
      return { success: true, data };
    } catch (error: any) {
      return {
        success: false,
        error:
          error.response?.data?.detail || "Failed to send exploration data",
      };
    }
  },
  getViewportChunks: async (
    minLat: number,
    maxLat: number,
    minLng: number,
    maxLng: number,
  ): Promise<ApiResponse<ViewportChunksResponse>> => {
    try {
      const data = await exploreApi.getViewportChunks(
        minLat,
        maxLat,
        minLng,
        maxLng,
      );
      return { success: true, data };
    } catch (error: any) {
      return {
        success: false,
        error: error.response?.data?.detail || "Failed to load explored areas",
      };
    }
  },
  getStats: async (): Promise<ApiResponse<ExplorationStatsResponse>> => {
    try {
      const data = await exploreApi.getStats();
      return { success: true, data };
    } catch (error: any) {
      return {
        success: false,
        error: error.response?.data?.detail || "Failed to load stats",
      };
    }
  },
};

// Xuất mặc định bản mới để chuẩn hóa từ đây về sau
export default exploreApi;
