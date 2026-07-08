/**
 * LAYERS — Onboarding Store
 * ==========================================
 * Zustand store for the story-mode onboarding flow.
 *
 * PATTERN: Same as authStore / notificationStore —
 *   create<State>((set, get) => ({ ...actions })) + SecureStore persistence.
 *
 * PERSISTENCE:
 *   - `layers_onboarding_complete` — "1" once the user finishes onboarding.
 *     Stored per-device (SecureStore), so reinstalls see onboarding again.
 *
 * LAYER CHOICE:
 *   The user picks their starting vibe (LIGHT / SHADOW) during onboarding.
 *   On completion we apply it to authStore so the whole app themes correctly.
 */

import { create } from "zustand";
import * as SecureStore from "expo-secure-store";
import { useAuthStore } from "./authStore";
import { Layer } from "../types";

// ============================================================
// CONSTANTS
// ============================================================

const ONBOARDING_KEY = "layers_onboarding_complete";

// ============================================================
// STATE
// ============================================================


interface OnboardingState {
    /** True once we've read the persisted flag from SecureStore. */
  isHydrated: boolean;

  /** True if this device has already finished onboarding. */
  hasCompletedOnboarding: boolean;

  /** The layer the user picked on the LayerChoice screen. */
  chosenLayer: Layer;

  // Actions
  hydrate: () => Promise<void>;
  chooseLayer: (layer: Layer) => void;
  completeOnboarding: () => Promise<void>;
  /** DEV ONLY — clears the flag so onboarding shows again on next launch. */
  resetOnboarding: () => Promise<void>;
}

// ============================================================
// STORE
// ============================================================

export const useOnboardingStore = create<OnboardingState>((set, get) => ({
  isHydrated: false,
  hasCompletedOnboarding: false,
  chosenLayer: "LIGHT",

  // ========================================================
  // HYDRATE — called once from RootNavigator on app start
  // ========================================================
  hydrate: async () => {
    try {
      const value = await SecureStore.getItemAsync(ONBOARDING_KEY);
      set({
        hasCompletedOnboarding: value === "1",
        isHydrated: true,
      });
    } catch (error) {
      console.error("[Onboarding] hydrate failed:", error);
      // Fail open — never trap the user in a broken loading state.
      set({ isHydrated: true });
    }
  },

  // ========================================================
  // CHOOSE LAYER — LayerChoice screen
  // ========================================================
  chooseLayer: (layer: Layer) => {
    set({ chosenLayer: layer });

    // Apply immediately so the rest of onboarding previews the chosen theme.
    // NOTE: if your authStore exposes a setLayer/toggleLayer action,
    // prefer calling that instead of setState (see SETUP.md §3).
    useAuthStore.setState({ layer });
  },

  // ========================================================
  // COMPLETE — FirstMission screen "Enter LAYERS" button
  // ========================================================
  completeOnboarding: async () => {
    try {
      await SecureStore.setItemAsync(ONBOARDING_KEY, "1");
    } catch (error) {
      // Persistence failure shouldn't block entry — worst case the user
      // sees onboarding once more on next launch.
      console.error("[Onboarding] persist failed:", error);
    }
    set({ hasCompletedOnboarding: true });
  },

  // ========================================================
  // RESET — dev helper (call from a hidden dev menu if needed)
  // ========================================================
  resetOnboarding: async () => {
    if (!__DEV__) return;
    try {
      await SecureStore.deleteItemAsync(ONBOARDING_KEY);
    } catch (error) {
      console.error("[Onboarding] reset failed:", error);
    }
    set({ hasCompletedOnboarding: false });
  },
}));