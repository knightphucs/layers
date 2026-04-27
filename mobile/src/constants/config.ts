// LAYERS Configuration
import Constants from "expo-constants";
import { Platform } from "react-native";

const getDevHost = (): string => {
  // 1. Explicit override via env var (most reliable, set in mobile/.env)
  if (process.env.EXPO_PUBLIC_API_HOST) {
    return process.env.EXPO_PUBLIC_API_HOST;
  }

  // 2. Auto-detect from Expo dev server's hostUri (LAN IP of dev machine)
  const hostUri = Constants.expoConfig?.hostUri; // e.g. "192.168.1.5:8081"
  if (hostUri) {
    return hostUri.split(":")[0];
  }

  // 3. Android emulator → host machine is reachable at 10.0.2.2
  if (Platform.OS === "android") {
    return "10.0.2.2";
  }

  // 4. iOS simulator / web → localhost
  return "localhost";
};

const getDevApiUrl = (): string => `http://${getDevHost()}:8000/api/v1`;
const getDevMinioUrl = (): string => `http://${getDevHost()}:9000`;

export const Config = {
  API_URL: __DEV__ ? getDevApiUrl() : "https://api.layers.app/v1",
  MINIO_URL: __DEV__ ? getDevMinioUrl() : "https://storage.layers.app",

  // Map Default Region (Ho Chi Minh City)
  MAP_DEFAULT_REGION: {
    latitude: 10.7769,
    longitude: 106.7009,
    latitudeDelta: 0.0922,
    longitudeDelta: 0.0421,
  },

  // Geo Settings (from Masterplan)
  GEO: {
    UNLOCK_RADIUS_METERS: 50, // Proof of Presence radius
    FOG_CHUNK_SIZE: 100, // Fog of War chunk size
    PAPER_PLANE_MIN_DISTANCE: 200, // Min distance for paper planes
    PAPER_PLANE_MAX_DISTANCE: 1000, // Max distance
    CAMPFIRE_RADIUS: 50, // Campfire chat radius
    NEARBY_RADIUS_DEFAULT: 1000, // Default search radius in meters
  },

  // Slow Mail Settings
  SLOW_MAIL: {
    MIN_DELAY_HOURS: 6,
    MAX_DELAY_HOURS: 12,
  },

  // Gamification
  GAMIFICATION: {
    XP_PER_ARTIFACT: 50,
    XP_PER_REPLY: 30,
    XP_PER_CHECK_IN: 10,
  },
};
