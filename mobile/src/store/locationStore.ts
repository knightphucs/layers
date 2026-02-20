// ===========================================
// LAYERS Location Store (Zustand)
// Manages user location & GPS tracking
// ===========================================

import { create } from "zustand";
import * as Location from "expo-location";

export interface Coordinates {
  latitude: number;
  longitude: number;
}

interface LocationState {
  // State
  currentLocation: Coordinates | null;
  lastKnownLocation: Coordinates | null;
  permissionStatus: Location.PermissionStatus | null;
  isLoading: boolean;
  error: string | null;
  isWatching: boolean;
  accuracy: number | null;
  heading: number | null;
  speed: number | null;

  // Actions
  requestPermission: () => Promise<boolean>;
  getCurrentLocation: () => Promise<Coordinates | null>;
  watchLocation: () => Promise<void>;
  stopWatching: () => void;
  setLocation: (location: Coordinates) => void;
  clearError: () => void;
  reset: () => void;
}

// Store the subscription outside for cleanup
let locationSubscription: Location.LocationSubscription | null = null;

export const useLocationStore = create<LocationState>((set, get) => ({
  // Initial State
  currentLocation: null,
  lastKnownLocation: null,
  permissionStatus: null,
  isLoading: false,
  error: null,
  isWatching: false,
  accuracy: null,
  heading: null,
  speed: null,

  // Request location permission
  requestPermission: async () => {
    try {
      // First check current status
      const { status: existingStatus } =
        await Location.getForegroundPermissionsAsync();

      if (existingStatus === "granted") {
        set({ permissionStatus: existingStatus });
        return true;
      }

      // Request permission
      const { status } = await Location.requestForegroundPermissionsAsync();
      set({ permissionStatus: status });

      if (status !== "granted") {
        set({ error: "Location permission denied" });
        return false;
      }

      return true;
    } catch (error) {
      console.error("Permission request failed:", error);
      set({ error: "Failed to request location permission" });
      return false;
    }
  },

  // Get current location once
  getCurrentLocation: async () => {
    const state = get();

    // Check permission first
    if (state.permissionStatus !== "granted") {
      const granted = await state.requestPermission();
      if (!granted) return null;
    }

    set({ isLoading: true, error: null });

    try {
      const location = await Location.getCurrentPositionAsync({
        accuracy: Location.Accuracy.High,
      });

      const coords: Coordinates = {
        latitude: location.coords.latitude,
        longitude: location.coords.longitude,
      };

      set({
        currentLocation: coords,
        lastKnownLocation: coords,
        accuracy: location.coords.accuracy,
        heading: location.coords.heading,
        speed: location.coords.speed,
        isLoading: false,
        error: null,
      });

      return coords;
    } catch (error: any) {
      console.error("Get location failed:", error);

      let errorMessage = "Failed to get current location";

      if (error.code === "E_LOCATION_SETTINGS_UNSATISFIED") {
        errorMessage =
          "Please enable location services in your device settings";
      } else if (error.code === "E_LOCATION_TIMEOUT") {
        errorMessage = "Location request timed out. Please try again.";
      }

      set({
        error: errorMessage,
        isLoading: false,
      });

      return null;
    }
  },

  // Watch location continuously
  watchLocation: async () => {
    const state = get();

    // Don't start multiple watchers
    if (state.isWatching) {
      console.log("Already watching location");
      return;
    }

    // Check permission
    if (state.permissionStatus !== "granted") {
      const granted = await state.requestPermission();
      if (!granted) return;
    }

    try {
      // Stop any existing subscription
      if (locationSubscription) {
        locationSubscription.remove();
      }

      locationSubscription = await Location.watchPositionAsync(
        {
          accuracy: Location.Accuracy.High,
          distanceInterval: 10, // Update every 10 meters
          timeInterval: 5000, // Or every 5 seconds
        },
        (location) => {
          const coords: Coordinates = {
            latitude: location.coords.latitude,
            longitude: location.coords.longitude,
          };

          set({
            currentLocation: coords,
            lastKnownLocation: coords,
            accuracy: location.coords.accuracy,
            heading: location.coords.heading,
            speed: location.coords.speed,
            error: null,
          });
        },
      );

      set({ isWatching: true, error: null });
      console.log("📍 Location watching started");
    } catch (error) {
      console.error("Watch location failed:", error);
      set({ error: "Failed to start location tracking" });
    }
  },

  // Stop watching location
  stopWatching: () => {
    if (locationSubscription) {
      locationSubscription.remove();
      locationSubscription = null;
    }
    set({ isWatching: false });
    console.log("📍 Location watching stopped");
  },

  // Manually set location (for testing)
  setLocation: (location: Coordinates) => {
    set({
      currentLocation: location,
      lastKnownLocation: location,
    });
  },

  // Clear error
  clearError: () => set({ error: null }),

  // Reset store
  reset: () => {
    if (locationSubscription) {
      locationSubscription.remove();
      locationSubscription = null;
    }
    set({
      currentLocation: null,
      lastKnownLocation: null,
      permissionStatus: null,
      isLoading: false,
      error: null,
      isWatching: false,
      accuracy: null,
      heading: null,
      speed: null,
    });
  },
}));
