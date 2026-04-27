/**
 * LAYERS — Connection Service (Week 5 Day 4)
 * ==========================================
 * API calls for the Progressive Connection System.
 *
 * PATTERN: Static methods, same as authService, inboxService, profileService.
 */

import api from "./api";
import {
  ConnectionListResponse,
  ConnectionStatsResponse,
  ConnectionLevel,
  UpgradeResponse,
} from "../types/connections";

// ============================================================
// CONNECTION SERVICE
// ============================================================

export const connectionService = {
  /**
   * List all connections with optional level filter.
   */
  listConnections: async (params?: {
    level?: ConnectionLevel;
    limit?: number;
    offset?: number;
  }): Promise<ConnectionListResponse> => {
    const queryParams: Record<string, string | number> = {
      limit: params?.limit ?? 50,
      offset: params?.offset ?? 0,
    };
    if (params?.level) {
      queryParams.level = params.level;
    }

    const response = await api.get<ConnectionListResponse>("/connections", {
      params: queryParams,
    });
    return response.data;
  },

  /**
   * Get connection statistics for profile screen.
   */
  getStats: async (): Promise<ConnectionStatsResponse> => {
    const response =
      await api.get<ConnectionStatsResponse>("/connections/stats");
    return response.data;
  },

  /**
   * Request to upgrade a SIGNAL connection to CONNECTED.
   * If other user has also requested → auto-upgrades.
   */
  requestUpgrade: async (connectionId: string): Promise<UpgradeResponse> => {
    const response = await api.post<UpgradeResponse>(
      `/connections/${connectionId}/request`,
    );
    return response.data;
  },

  /**
   * Accept an incoming upgrade request.
   * Same effect as requestUpgrade — symmetric.
   */
  acceptUpgrade: async (connectionId: string): Promise<UpgradeResponse> => {
    const response = await api.post<UpgradeResponse>(
      `/connections/${connectionId}/accept`,
    );
    return response.data;
  },

  /**
   * Reject an incoming upgrade request.
   */
  rejectUpgrade: async (connectionId: string): Promise<UpgradeResponse> => {
    const response = await api.post<UpgradeResponse>(
      `/connections/${connectionId}/reject`,
    );
    return response.data;
  },
};
