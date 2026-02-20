/**
 * LAYERS - Haptic Feedback Utility
 * Adds physical feedback to important interactions
 *
 * WHY: Location-based apps feel MORE real with haptics.
 * When you unlock an artifact within 50m → BUZZ! Dopamine hit.
 *
 * USAGE:
 *   import { haptics } from '../utils/haptics';
 *   haptics.impact();        // Button press
 *   haptics.success();       // Artifact unlocked!
 *   haptics.error();         // Something failed
 *   haptics.selection();     // Tab change, toggle
 */

import * as Haptics from "expo-haptics";

export const haptics = {
  /** Light tap - for button presses, toggles */
  impact: () => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
  },

  /** Light impact - subtle feedback */
  light: () => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
  },

  /** Heavy impact - important actions (artifact found!) */
  heavy: () => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy);
  },

  /** Success pattern - artifact unlocked, letter sent */
  success: () => {
    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
  },

  /** Error pattern - action failed */
  error: () => {
    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
  },

  /** Warning pattern - approaching geo boundary */
  warning: () => {
    Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning);
  },

  /** Selection tick - tab changes, picker scrolling */
  selection: () => {
    Haptics.selectionAsync();
  },

  /**
   * Custom pattern - for special moments
   * E.g., when entering a Glitch Zone in Shadow Layer
   */
  glitchZone: async () => {
    // Quick triple buzz - feels eerie!
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy);
    await new Promise((r) => setTimeout(r, 100));
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    await new Promise((r) => setTimeout(r, 80));
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy);
  },

  /**
   * Heartbeat pattern - for emotional moments
   * E.g., when reading a letter from someone
   */
  heartbeat: async () => {
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    await new Promise((r) => setTimeout(r, 150));
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy);
    await new Promise((r) => setTimeout(r, 400));
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    await new Promise((r) => setTimeout(r, 150));
    Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy);
  },
};
