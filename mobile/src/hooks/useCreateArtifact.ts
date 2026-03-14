/**
 * LAYERS - useCreateArtifact Hook
 * ====================================
 * FILE: mobile/src/hooks/useCreateArtifact.ts
 *
 * Orchestrates the full artifact creation flow:
 *   1. Open sheet → user fills form
 *   2. Submit → POST /artifacts with GPS location
 *   3. Close sheet → play drop animation
 *   4. Animation completes → new marker visible on map
 *   5. Refresh nearby artifacts
 *
 * Separates creation logic from MapScreen to keep it clean.
 */

import { useState, useCallback } from "react";
import { useLocationStore } from "../store/locationStore";
import { useArtifactStore } from "../store/artifactStore";
import { CreateArtifactData } from "../components/create/CreateArtifactSheet";
import { ContentType, Layer, MARKER_CONFIGS, Visibility } from "../types/artifact";

// ============================================================
// TYPES
// ============================================================

interface DropAnimState {
  visible: boolean;
  emoji: string;
}

// ============================================================
// HOOK
// ============================================================

export function useCreateArtifact() {
  // Sheet visibility
  const [isSheetOpen, setIsSheetOpen] = useState(false);

  // Drop animation state
  const [dropAnim, setDropAnim] = useState<DropAnimState>({
    visible: false,
    emoji: "✉️",
  });

  // Error state
  const [error, setError] = useState<string | null>(null);

  // Stores
  const { currentLocation, lastKnownLocation } = useLocationStore();
  const location = currentLocation ?? lastKnownLocation;
  const { createArtifact, fetchNearby } = useArtifactStore();

  // ========================================================
  // OPEN / CLOSE SHEET
  // ========================================================

  const openSheet = useCallback(() => {
    if (!location) {
      setError("GPS location not available. Please enable location services.");
      return;
    }
    setError(null);
    setIsSheetOpen(true);
  }, [location]);

  const closeSheet = useCallback(() => {
    setIsSheetOpen(false);
  }, []);

  // ========================================================
  // SUBMIT — Create artifact via API
  // ========================================================

  const handleSubmit = useCallback(
    async (data: CreateArtifactData) => {
      if (!location) {
        throw new Error("No GPS location available");
      }

      const contentType = ContentType[data.content_type];
      const visibility = Visibility[data.visibility];
      const layer = Layer[data.layer as keyof typeof Layer];

      // Build request matching backend ArtifactCreate schema
      const request = {
        latitude: location.latitude,
        longitude: location.longitude,
        content_type: contentType,
        payload: data.payload,
        visibility,
        passcode: data.passcode,
        target_username: data.target_username,
        layer,
      };

      // Call backend
      await createArtifact(request);

      // Close sheet
      setIsSheetOpen(false);

      // Get emoji for animation
      const config = MARKER_CONFIGS[contentType] || MARKER_CONFIGS.LETTER;
      const emoji = layer === Layer.SHADOW ? config.shadowEmoji : config.emoji;

      // Show drop animation
      setDropAnim({ visible: true, emoji });
    },
    [location, createArtifact],
  );

  // ========================================================
  // ANIMATION COMPLETE — Refresh markers
  // ========================================================

  const handleAnimComplete = useCallback(() => {
    setDropAnim({ visible: false, emoji: "✉️" });

    // Refresh nearby artifacts to show the new one
    if (location) {
      fetchNearby(location.latitude, location.longitude, 1000);
    }
  }, [location, fetchNearby]);

  return {
    // Sheet
    isSheetOpen,
    openSheet,
    closeSheet,

    // Creation
    handleSubmit,

    // Animation
    dropAnim,
    handleAnimComplete,

    // Error
    error,
    clearError: () => setError(null),
  };
}
