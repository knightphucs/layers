// ============ USER ============
export interface User {
  id: string;
  email: string;
  username: string;
  avatar_url?: string;
  bio?: string;
  xp: number;
  level: number;
  reputation_score: number;
  role: "USER" | "ADMIN" | "PARTNER";
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// ============ AUTH ============
export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  username: string;
  password: string;
}

export interface AuthResponse {
  user: User;
  access_token: string;
  refresh_token: string;
  token_type: string;
}

// ============ LOCATION ============
export type Layer = "LIGHT" | "SHADOW";

export type LocationCategory =
  | "CAFE"
  | "PARK"
  | "GHOST"
  | "VOUCHER"
  | "LANDMARK"
  | "HIDDEN_GEM"
  | "GLITCH_ZONE";

export interface Location {
  id: string;
  latitude: number;
  longitude: number;
  layer: Layer;
  category: LocationCategory;
  name?: string;
  description?: string;
  metadata?: Record<string, any>;
  created_at: string;
}

// ============ ARTIFACT ============
export type ArtifactContentType =
  | "LETTER"
  | "VOUCHER"
  | "AUDIO"
  | "NOTEBOOK"
  | "TIME_CAPSULE"
  | "PAPER_PLANE";

export type ArtifactVisibility = "PUBLIC" | "TARGETED" | "PASSCODE";

export interface Artifact {
  id: string;
  location_id: string;
  user_id: string;
  content_type: ArtifactContentType;
  visibility: ArtifactVisibility;
  target_user_id?: string; // For TARGETED visibility
  payload: Record<string, any>; // Flexible JSONB content
  unlock_conditions?: {
    time_start?: string; // For Midnight Lock
    time_end?: string;
    unlock_date?: string; // For Time Capsule
  };
  is_active: boolean;
  created_at: string;
  updated_at: string;

  // Joined data
  location?: Location;
  user?: Pick<User, "id" | "username" | "avatar_url">;
  distance_meters?: number; // Calculated by PostGIS
}

// ============ CONNECTION ============
export type ConnectionStatus = "PENDING" | "CONNECTED";

export interface Connection {
  id: string;
  user_a_id: string;
  user_b_id: string;
  interaction_count: number;
  status: ConnectionStatus;
  created_at: string;
  connected_at?: string;

  // Joined data
  other_user?: Pick<User, "id" | "username" | "avatar_url">;
}

// ============ INVENTORY ============
export interface InventoryItem {
  id: string;
  user_id: string;
  artifact_id: string;
  saved_at: string;
  is_used: boolean; // For vouchers

  // Joined
  artifact?: Artifact;
}

// ============ FOG OF WAR ============
export interface ExploredChunk {
  user_id: string;
  chunk_x: number;
  chunk_y: number;
  explored_at: string;
}

// ============ API RESPONSES ============
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface NearbyArtifactsResponse {
  artifacts: Artifact[];
  user_location: {
    latitude: number;
    longitude: number;
  };
}

// ============ NAVIGATION ============
export type AuthStackParamList = {
  Login: undefined;
  Register: undefined;
  ForgotPassword: undefined;
};

export type MainTabParamList = {
  Map: undefined;
  Explore: undefined;
  Profile: undefined;
};

export type RootStackParamList = {
  Auth: undefined;
  Main: undefined;
};
