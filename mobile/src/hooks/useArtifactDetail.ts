/**
 * LAYERS - useArtifactDetail Hook
 * ====================================
 * FILE: mobile/src/hooks/useArtifactDetail.ts
 *
 * Orchestrates artifact viewing/unlocking:
 *   1. User taps marker → fetchDetail(artifactId)
 *   2. Backend returns lock status + distance
 *   3. If unlocked → show content
 *   4. If passcode → user enters code → verify → show content
 *   5. User can reply via Slow Mail
 *
 * CONNECTS TO:
 *   GET  /api/v1/artifacts/{id}?lat=X&lng=Y
 *   POST /api/v1/artifacts/{id}/unlock?passcode=X&lat=X&lng=Y
 *   POST /api/v1/artifacts/{id}/reply
 */

import { useState, useCallback } from "react";
import { useLocationStore } from "../store/locationStore";
import ArtifactApi from "../services/artifactApi";
import { ArtifactDetailData } from "../components/detail/ArtifactDetailSheet";

const TARGETED_LOCK_MESSAGE = "This artifact is for someone else";

function createLockedFallbackData(
  artifactId: string,
  lockReason: string,
  visibility: "PUBLIC" | "TARGETED" = "PUBLIC",
): ArtifactDetailData {
  return {
    id: artifactId,
    content_type: "LETTER",
    layer: "LIGHT",
    visibility,
    latitude: 0,
    longitude: 0,
    is_locked: true,
    lock_reason: visibility === "TARGETED" ? TARGETED_LOCK_MESSAGE : lockReason,
    view_count: 0,
    reply_count: 0,
    save_count: 0,
    created_at: new Date().toISOString(),
  };
}

export function useArtifactDetail() {
  const [isDetailOpen, setIsDetailOpen] = useState(false);
  const [detailData, setDetailData] = useState<ArtifactDetailData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [currentArtifactId, setCurrentArtifactId] = useState<string | null>(
    null,
  );

  const { currentLocation: location } = useLocationStore();

  // ========================================================
  // FETCH DETAIL — When user taps a marker
  // ========================================================

  const openDetail = useCallback(
    async (artifactId: string) => {
      setCurrentArtifactId(artifactId);
      setIsDetailOpen(true);
      setIsLoading(true);
      setDetailData(null);

      try {
        const result = await ArtifactApi.getDetail(
          artifactId,
          location?.latitude,
          location?.longitude,
        );

        if (result.success && result.data) {
          setDetailData(result.data as unknown as ArtifactDetailData);
        } else if (result.error === "This artifact no longer exists") {
          setDetailData(null);
        } else {
          const errorText = result.error || "Failed to load artifact";
          const isTargetedLock = errorText
            .toLowerCase()
            .includes("someone else");
          setDetailData(
            createLockedFallbackData(
              artifactId,
              isTargetedLock ? TARGETED_LOCK_MESSAGE : errorText,
              isTargetedLock ? "TARGETED" : "PUBLIC",
            ),
          );
        }
      } catch (error) {
        console.error("[ArtifactDetail] Fetch failed:", error);
        setDetailData(createLockedFallbackData(artifactId, "Failed to load artifact"));
      } finally {
        setIsLoading(false);
      }
    },
    [location],
  );

  const closeDetail = useCallback(() => {
    setIsDetailOpen(false);
    setCurrentArtifactId(null);
  }, []);

  // ========================================================
  // UNLOCK PASSCODE — Verify code with backend
  // ========================================================

  const unlockPasscode = useCallback(
    async (passcode: string): Promise<boolean> => {
      if (!currentArtifactId || !location) return false;

      try {
        const result = await ArtifactApi.unlock(
          currentArtifactId,
          passcode,
          location.latitude,
          location.longitude,
        );

        if (result.success && result.data) {
          const unlocked = result.data as unknown as ArtifactDetailData;

          if (unlocked.payload) {
            setDetailData((prev) =>
              prev
                ? {
                    ...prev,
                    is_locked: false,
                    lock_reason: undefined,
                    payload: unlocked.payload,
                    view_count: unlocked.view_count ?? prev.view_count,
                  }
                : unlocked,
            );
            return true;
          }
        }

        if (result.error) {
          throw new Error(result.error);
        }

        return false;
      } catch (error: unknown) {
        const message =
          error instanceof Error ? error.message : "Failed to unlock";
        throw new Error(message);
      }
    },
    [currentArtifactId, location],
  );

  // ========================================================
  // REPLY — Send Slow Mail reply
  // ========================================================

  const sendReply = useCallback(
    async (content: string) => {
      if (!currentArtifactId || !location) return;

      try {
        const result = await ArtifactApi.reply(
          currentArtifactId,
          content,
          location.latitude,
          location.longitude,
        );

        if (!result.success) {
          throw new Error(result.error || "Failed to send reply");
        }

        setDetailData((prev) =>
          prev ? { ...prev, reply_count: prev.reply_count + 1 } : prev,
        );
      } catch (error: unknown) {
        const message =
          error instanceof Error ? error.message : "Failed to send reply";
        throw new Error(message);
      }
    },
    [currentArtifactId, location],
  );

  return {
    // Sheet state
    isDetailOpen,
    detailData,
    isLoading,

    // Actions
    openDetail,
    closeDetail,
    unlockPasscode,
    sendReply,
  };
}
