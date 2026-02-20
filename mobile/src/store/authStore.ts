// ===========================================
// LAYERS Auth Store (Zustand)
// Manages user authentication state
// ===========================================

import { create } from "zustand";
import * as SecureStore from "expo-secure-store";
import { User, AuthTokens, Layer } from "../types";

interface AuthState {
  // State
  user: User | null;
  tokens: AuthTokens | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  layer: Layer;

  // Actions
  setUser: (user: User | null) => void;
  setTokens: (tokens: AuthTokens | null) => void;
  setLoading: (loading: boolean) => void;
  toggleLayer: () => void;
  setLayer: (layer: Layer) => void;
  login: (user: User, tokens: AuthTokens) => Promise<void>;
  logout: () => Promise<void>;
  loadStoredAuth: () => Promise<void>;
  updateUser: (updates: Partial<User>) => void;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  // Initial State
  user: null,
  tokens: null,
  isLoading: true,
  isAuthenticated: false,
  layer: "LIGHT",

  // Actions
  setUser: (user) =>
    set({
      user,
      isAuthenticated: !!user,
    }),

  setTokens: (tokens) => set({ tokens }),

  setLoading: (isLoading) => set({ isLoading }),

  toggleLayer: () =>
    set((state) => ({
      layer: state.layer === "LIGHT" ? "SHADOW" : "LIGHT",
    })),

  setLayer: (layer) => set({ layer }),

  login: async (user, tokens) => {
    try {
      // Store tokens securely
      await SecureStore.setItemAsync("access_token", tokens.access_token);
      await SecureStore.setItemAsync("refresh_token", tokens.refresh_token);
      await SecureStore.setItemAsync("user", JSON.stringify(user));

      set({
        user,
        tokens,
        isAuthenticated: true,
        isLoading: false,
      });
    } catch (error) {
      console.error("Failed to store auth:", error);
      throw error;
    }
  },

  logout: async () => {
    try {
      // Clear secure storage
      await SecureStore.deleteItemAsync("access_token");
      await SecureStore.deleteItemAsync("refresh_token");
      await SecureStore.deleteItemAsync("user");

      set({
        user: null,
        tokens: null,
        isAuthenticated: false,
      });
    } catch (error) {
      console.error("Failed to clear auth:", error);
    }
  },

  loadStoredAuth: async () => {
    try {
      const accessToken = await SecureStore.getItemAsync("access_token");
      const refreshToken = await SecureStore.getItemAsync("refresh_token");
      const userStr = await SecureStore.getItemAsync("user");

      if (accessToken && refreshToken && userStr) {
        const user = JSON.parse(userStr) as User;
        set({
          user,
          tokens: {
            access_token: accessToken,
            refresh_token: refreshToken,
            token_type: "bearer",
          },
          isAuthenticated: true,
          isLoading: false,
        });
      } else {
        set({ isLoading: false });
      }
    } catch (error) {
      console.error("Error loading stored auth:", error);
      set({ isLoading: false });
    }
  },

  updateUser: (updates) =>
    set((state) => ({
      user: state.user ? { ...state.user, ...updates } : null,
    })),
}));
