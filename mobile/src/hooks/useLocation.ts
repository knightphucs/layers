// ===========================================
// Handles all location-related functionality
// ===========================================

import { useEffect, useCallback, useRef } from "react";
import * as Location from "expo-location";
import { Alert, Linking, Platform } from "react-native";
import { useLocationStore } from "../store/locationStore";

interface UseLocationOptions {
  // Auto-request permission on mount
  autoRequest?: boolean;
  // Auto-start watching location
  autoWatch?: boolean;
  // Show alert when permission denied
  showDeniedAlert?: boolean;
}

export function useLocation(options: UseLocationOptions = {}) {
  const {
    autoRequest = true,
    autoWatch = false,
    showDeniedAlert = true,
  } = options;

  const {
    currentLocation,
    permissionStatus,
    isLoading,
    error,
    isWatching,
    requestPermission,
    getCurrentLocation,
    watchLocation,
    stopWatching,
    clearError,
  } = useLocationStore();

  const hasRequestedRef = useRef(false);

  // Show permission denied alert
  const showPermissionDeniedAlert = useCallback(() => {
    Alert.alert(
      "Location Permission Required",
      "LAYERS needs access to your location to show nearby memories and artifacts. Please enable location in your device settings.",
      [
        {
          text: "Cancel",
          style: "cancel",
        },
        {
          text: "Open Settings",
          onPress: () => {
            if (Platform.OS === "ios") {
              Linking.openURL("app-settings:");
            } else {
              Linking.openSettings();
            }
          },
        },
      ],
    );
  }, []);

  // Initialize location
  const initializeLocation = useCallback(async () => {
    if (hasRequestedRef.current) return;
    hasRequestedRef.current = true;

    // Request permission
    const granted = await requestPermission();

    if (granted) {
      // Get initial location
      await getCurrentLocation();

      // Start watching if autoWatch enabled
      if (autoWatch) {
        await watchLocation();
      }
    } else if (showDeniedAlert) {
      showPermissionDeniedAlert();
    }
  }, [
    requestPermission,
    getCurrentLocation,
    watchLocation,
    autoWatch,
    showDeniedAlert,
    showPermissionDeniedAlert,
  ]);

  // Auto-initialize on mount
  useEffect(() => {
    if (autoRequest) {
      initializeLocation();
    }

    // Cleanup: stop watching on unmount
    return () => {
      if (isWatching) {
        stopWatching();
      }
    };
  }, []);

  // Retry getting location
  const retry = useCallback(async () => {
    clearError();

    const granted = await requestPermission();

    if (granted) {
      await getCurrentLocation();
    } else if (showDeniedAlert) {
      showPermissionDeniedAlert();
    }
  }, [
    requestPermission,
    getCurrentLocation,
    clearError,
    showDeniedAlert,
    showPermissionDeniedAlert,
  ]);

  // Check if user is within radius of a point
  const isWithinRadius = useCallback(
    (targetLat: number, targetLng: number, radiusMeters: number): boolean => {
      if (!currentLocation) return false;

      const distance = calculateDistance(
        currentLocation.latitude,
        currentLocation.longitude,
        targetLat,
        targetLng,
      );

      return distance <= radiusMeters;
    },
    [currentLocation],
  );

  // Calculate distance to a point
  const getDistanceTo = useCallback(
    (targetLat: number, targetLng: number): number | null => {
      if (!currentLocation) return null;

      return calculateDistance(
        currentLocation.latitude,
        currentLocation.longitude,
        targetLat,
        targetLng,
      );
    },
    [currentLocation],
  );

  // Format distance for display
  const formatDistance = useCallback((meters: number): string => {
    if (meters < 1000) {
      return `${Math.round(meters)}m`;
    }
    return `${(meters / 1000).toFixed(1)}km`;
  }, []);

  return {
    // State
    location: currentLocation,
    permissionStatus,
    isLoading,
    error,
    isWatching,

    // Computed
    hasPermission: permissionStatus === "granted",
    isPermissionDenied: permissionStatus === "denied",

    // Actions
    requestPermission,
    getCurrentLocation,
    watchLocation,
    stopWatching,
    retry,
    clearError,

    // Helpers
    isWithinRadius,
    getDistanceTo,
    formatDistance,
  };
}

// ============================================
// HELPER: Calculate distance using Haversine formula
// ============================================
function calculateDistance(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number,
): number {
  const R = 6371e3; // Earth's radius in meters
  const φ1 = (lat1 * Math.PI) / 180;
  const φ2 = (lat2 * Math.PI) / 180;
  const Δφ = ((lat2 - lat1) * Math.PI) / 180;
  const Δλ = ((lon2 - lon1) * Math.PI) / 180;

  const a =
    Math.sin(Δφ / 2) * Math.sin(Δφ / 2) +
    Math.cos(φ1) * Math.cos(φ2) * Math.sin(Δλ / 2) * Math.sin(Δλ / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

  return R * c; // Distance in meters
}

// Export the helper for use elsewhere
export { calculateDistance };
