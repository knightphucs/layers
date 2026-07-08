/**
 * LAYERS — FirstMissionScreen
 * ==========================================
 * The final onboarding beat: hand the user a mission, not a menu.
 * (Masterplan "Single-player Experience" fix — new users need an
 * immediate goal, not an empty map.)
 *
 * Tapping "Enter LAYERS" calls completeOnboarding() — RootNavigator
 * reacts to the store change and switches to MainNavigator (Map tab).
 * No manual navigation reset needed.
 */

import React, { useRef, useEffect, useCallback, useState } from "react";
import {
  View,
  Text,
  Animated,
  TouchableOpacity,
  StyleSheet,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { FIRST_MISSIONS } from "../../types/onboarding";
import { useOnboardingStore } from "../../store/onboardingStore";
import { useAuthStore } from "../../store/authStore";
import { Colors } from "../../constants/colors";

export default function FirstMissionScreen() {
  const { completeOnboarding } = useOnboardingStore();
  const { layer } = useAuthStore();
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];

  const [isEntering, setIsEntering] = useState(false);

  // Entrance: fade + slide up (one orchestrated moment, not scattered fx)
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const slideAnim = useRef(new Animated.Value(24)).current;
  const glowAnim = useRef(new Animated.Value(0.3)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 600,
        useNativeDriver: true,
      }),
      Animated.timing(slideAnim, {
        toValue: 0,
        duration: 600,
        useNativeDriver: true,
      }),
    ]).start();

    // Gentle glow on the CTA — same language as ArtifactMarker in-range glow
    const glow = Animated.loop(
      Animated.sequence([
        Animated.timing(glowAnim, {
          toValue: 0.8,
          duration: 1000,
          useNativeDriver: true,
        }),
        Animated.timing(glowAnim, {
          toValue: 0.3,
          duration: 1000,
          useNativeDriver: true,
        }),
      ]),
    );
    glow.start();
    return () => glow.stop();
  }, [fadeAnim, slideAnim, glowAnim]);

  const handleEnter = useCallback(async () => {
    if (isEntering) return;
    setIsEntering(true);
    await completeOnboarding();
    // RootNavigator switches to MainNavigator automatically.
  }, [isEntering, completeOnboarding]);

  return (
    <SafeAreaView
      style={[styles.container, { backgroundColor: colors.background }]}
      edges={["top", "bottom"]}
    >
      <Animated.View
        style={[
          styles.content,
          { opacity: fadeAnim, transform: [{ translateY: slideAnim }] },
        ]}
      >
        <Text style={styles.headerEmoji}>🌫️</Text>
        <Text style={[styles.header, { color: colors.text }]}>
          The fog is waiting
        </Text>
        <Text style={[styles.subHeader, { color: colors.textSecondary }]}>
          Your first missions are live. Every step outside lifts the fog and
          earns XP.
        </Text>

        {FIRST_MISSIONS.map((mission, i) => (
          <View
            key={i}
            style={[
              styles.missionCard,
              {
                backgroundColor: colors.surface ?? colors.background,
                borderColor: colors.border ?? "rgba(128,128,128,0.3)",
              },
            ]}
          >
            <Text style={styles.missionIcon}>{mission.icon}</Text>
            <View style={styles.missionContent}>
              <Text style={[styles.missionTitle, { color: colors.text }]}>
                {mission.title}
              </Text>
              <Text
                style={[styles.missionDesc, { color: colors.textSecondary }]}
              >
                {mission.description}
              </Text>
            </View>
            <View style={[styles.xpBadge, { backgroundColor: colors.primary }]}>
              <Text style={styles.xpText}>+{mission.xpReward} XP</Text>
            </View>
          </View>
        ))}
      </Animated.View>

      <View style={styles.footer}>
        {/* Glow ring behind CTA */}
        <Animated.View
          style={[
            styles.ctaGlow,
            { backgroundColor: colors.primary, opacity: glowAnim },
          ]}
        />
        <TouchableOpacity
          style={[styles.enterButton, { backgroundColor: colors.primary }]}
          onPress={handleEnter}
          disabled={isEntering}
          accessibilityRole="button"
          accessibilityLabel="Enter LAYERS"
        >
          <Text style={styles.enterText}>
            {isEntering ? "Opening the map..." : "Enter LAYERS 🌆"}
          </Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

// ============================================================
// STYLES
// ============================================================

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  content: {
    flex: 1,
    paddingHorizontal: 24,
    paddingTop: 32,
  },
  headerEmoji: {
    fontSize: 56,
    textAlign: "center",
    marginBottom: 16,
  },
  header: {
    fontSize: 26,
    fontWeight: "800",
    textAlign: "center",
    marginBottom: 8,
  },
  subHeader: {
    fontSize: 14,
    lineHeight: 20,
    textAlign: "center",
    marginBottom: 32,
  },
  missionCard: {
    flexDirection: "row",
    alignItems: "center",
    borderWidth: 1,
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
    gap: 12,
  },
  missionIcon: {
    fontSize: 28,
  },
  missionContent: {
    flex: 1,
  },
  missionTitle: {
    fontSize: 15,
    fontWeight: "700",
    marginBottom: 2,
  },
  missionDesc: {
    fontSize: 12,
    lineHeight: 17,
  },
  xpBadge: {
    borderRadius: 12,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  xpText: {
    color: "#FFFFFF",
    fontSize: 12,
    fontWeight: "800",
  },
  footer: {
    paddingHorizontal: 24,
    paddingBottom: 24,
    alignItems: "center",
  },
  ctaGlow: {
    position: "absolute",
    bottom: 20,
    width: "80%",
    height: 60,
    borderRadius: 30,
    transform: [{ scale: 1.06 }],
  },
  enterButton: {
    width: "100%",
    borderRadius: 28,
    paddingVertical: 18,
    alignItems: "center",
  },
  enterText: {
    color: "#FFFFFF",
    fontSize: 17,
    fontWeight: "800",
    letterSpacing: 0.5,
  },
});
