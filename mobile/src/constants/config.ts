// LAYERS Configuration
import Constants from "expo-constants";

// Auto-detect dev machine IP from Expo dev server
const getDevApiUrl = (): string => {
  const hostUri = Constants.expoConfig?.hostUri; // e.g. "192.168.0.102:8081"
  if (hostUri) {
    const host = hostUri.split(":")[0];
    return `http://${host}:8000/api/v1`;
  }
  return "http://localhost:8000/api/v1";
};

export const Config = {
  API_URL: __DEV__ ? getDevApiUrl() : "https://api.layers.app/v1",

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
