/**
 * LAYERS — Navigation Ref + Deep Linking
 * ==========================================
 * Closes the Week 5 TODO in useNotifications.ts:
 *   "TODO Week 5 Day 4: Wire up React Navigation deep linking"
 *
 * HOW IT WORKS:
 *   - `navigationRef` attaches to <NavigationContainer> in App.tsx
 *   - `navigateFromNotification(data)` maps a push notification's
 *     `screen` field onto the real navigator tree
 *   - If navigation isn't ready yet (cold start from a notification),
 *     the intent is queued and flushed via `flushPendingNavigation()`
 *     from NavigationContainer's onReady.
 *
 * ⚠️ ADJUST THE MAPPING TABLE below to match your MainNavigator's
 *    actual tab/screen names — see SETUP.md §3.
 */

import { createNavigationContainerRef } from "@react-navigation/native";

export const navigationRef = createNavigationContainerRef();

// ============================================================
// PENDING INTENT (cold-start safety)
// ============================================================

let pendingNavigation: { name: string; params?: object } | null = null;

export function flushPendingNavigation() {
  if (pendingNavigation && navigationRef.isReady()) {
    const { name, params } = pendingNavigation;
    pendingNavigation = null;
    // @ts-expect-error — dynamic route name from notification payload
    navigationRef.navigate(name, params);
  }
}

// ============================================================
// NOTIFICATION → SCREEN MAPPING
// ============================================================

/**
 * Maps backend notification `screen` values to navigator routes.
 * KEY   = the `data.screen` string your backend sends in the push payload
 * VALUE = the route name in MainNavigator (⚠️ adjust to your tab names!)
 */
const SCREEN_MAP: Record<string, string> = {
  Inbox: "Inbox",
  Map: "Map",
  Profile: "Profile",
  Leaderboard: "Ranks",
  Messages: "Profile", // chat lives behind Profile → Messages for now
};

/**
 * Navigate from a tapped push notification.
 * Never throws — deep linking must not crash the app.
 */
export function navigateFromNotification(data: {
  screen?: string;
  params?: object;
}) {
  try {
    if (!data?.screen) return;

    const routeName = SCREEN_MAP[data.screen] ?? data.screen;
    const intent = { name: routeName, params: data.params };

    if (!navigationRef.isReady()) {
      // Cold start: queue and let onReady flush it
      pendingNavigation = intent;
      return;
    }

    // @ts-expect-error — dynamic route name from notification payload
    navigationRef.navigate(intent.name, intent.params);
  } catch (error) {
    console.error("[DeepLink] navigation failed:", error);
  }
}
