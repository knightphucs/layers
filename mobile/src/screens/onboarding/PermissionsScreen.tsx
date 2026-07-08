/**
 * LAYERS — PermissionScreen
 * ==========================================
 * Permission PRIMING done right:
 *   - Explain WHY before the OS dialog appears (higher grant rates)
 *   - Location = required (core loop can't work without it)
 *   - Notifications = optional (skippable, changeable later in Settings)
 *
 * Uses expo-location + expo-notifications (both already in the project
 * from Week 3 map work and Week 5 push notifications — no new deps).
 */

import React, { useState, useCallback } from "react";
import { View, Text, ScrollView, TouchableOpacity, StyleSheet } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";
import * as Location from "expo-location";
import * as Notifications from "expo-notifications";

import {
  OnboardingStackParamList,
  PERMISSION_ITEMS,
  PermissionItem,
  PermissionKey,
  PermissionStatus,
} from "../../types/onboarding";
import { useOnboardingStore } from "../../store/onboardingStore";
import { PermissionCard } from "../../components/onboarding";
import { Colors } from "../../constants/colors";
import { useAuthStore } from "../../store/authStore";

type Props = {
  navigation: NativeStackNavigationProp<OnboardingStackParamList, "Permissions">;
};

export default function PermissionScreen({ navigation }: Props) {
  const { chosenLayer } = useOnboardingStore();
  const { layer } = useAuthStore();
  // Theme follows the layer chosen on the previous screen
  const activeLayer = (layer || chosenLayer).toLowerCase() as "light" | "shadow";
  const colors = Colors[activeLayer];

  const [statuses, setStatuses] = useState<Record<PermissionKey, PermissionStatus>>({
    location: "unknown",
    notifications: "unknown",
  });

  const setStatus = useCallback((key: PermissionKey, status: PermissionStatus) => {
    setStatuses((prev) => ({ ...prev, [key]: status }));
  }, []);

  // ========================================================
  // REQUEST HANDLERS
  // ========================================================

  const handleRequest = useCallback(
    async (item: PermissionItem) => {
      try {
        if (item.key === "location") {
          const { status } = await Location.requestForegroundPermissionsAsync();
          setStatus("location", status === "granted" ? "granted" : "denied");
        } else {
          const { status } = await Notifications.requestPermissionsAsync();
          setStatus("notifications", status === "granted" ? "granted" : "denied");
        }
      } catch (error) {
        console.error(`[Onboarding] ${item.key} permission failed:`, error);
        setStatus(item.key, "denied");
      }
    },
    [setStatus],
  );

  // ========================================================
  // CONTINUE — location must be granted; notifications optional
  // ========================================================

  const canContinue = statuses.location === "granted";

  const handleContinue = useCallback(() => {
    navigation.navigate("FirstMission");
  }, [navigation]);

  return (
    <SafeAreaView
      style={[styles.container, { backgroundColor: colors.background }]}
      edges={["top", "bottom"]}
    >
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={styles.headerEmoji}>🗝️</Text>
        <Text style={[styles.header, { color: colors.text }]}>
          Two keys to the city
        </Text>
        <Text style={[styles.subHeader, { color: colors.textSecondary }]}>
          LAYERS lives on your real map. Here's exactly what we need and why —
          nothing more.
        </Text>

        {PERMISSION_ITEMS.map((item) => (
          <PermissionCard
            key={item.key}
            item={item}
            status={statuses[item.key]}
            onRequest={handleRequest}
            colors={{
              surface: colors.surface ?? colors.background,
              text: colors.text,
              textSecondary: colors.textSecondary,
              primary: colors.primary,
              border: colors.border ?? "rgba(128,128,128,0.3)",
            }}
          />
        ))}

        <Text style={[styles.privacyNote, { color: colors.textSecondary }]}>
          🔒 Your exact location is never shown to other users. Artifacts only
          reveal an approximate area, and anonymous mode hides you completely.
        </Text>
      </ScrollView>

      <View style={styles.footer}>
        <TouchableOpacity
          style={[
            styles.continueButton,
            { backgroundColor: colors.primary, opacity: canContinue ? 1 : 0.5 },
          ]}
          onPress={handleContinue}
          disabled={!canContinue}
          accessibilityRole="button"
          accessibilityLabel="Continue to first mission"
        >
          <Text style={styles.continueText}>
            {canContinue ? "Continue →" : "Location is required to play"}
          </Text>
        </TouchableOpacity>
        {statuses.notifications === "unknown" && canContinue && (
          <Text style={[styles.skipNote, { color: colors.textSecondary }]}>
            You can enable notifications later in Profile → Notifications.
          </Text>
        )}
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
  scroll: {
    paddingHorizontal: 24,
    paddingTop: 16,
    paddingBottom: 24,
  },
  headerEmoji: {
    fontSize: 48,
    textAlign: "center",
    marginBottom: 12,
  },
  header: {
    fontSize: 24,
    fontWeight: "800",
    textAlign: "center",
    marginBottom: 8,
  },
  subHeader: {
    fontSize: 14,
    lineHeight: 20,
    textAlign: "center",
    marginBottom: 24,
  },
  privacyNote: {
    fontSize: 12,
    lineHeight: 18,
    textAlign: "center",
    marginTop: 8,
    paddingHorizontal: 12,
  },
  footer: {
    paddingHorizontal: 24,
    paddingBottom: 16,
    gap: 8,
  },
  continueButton: {
    borderRadius: 28,
    paddingVertical: 16,
    alignItems: "center",
  },
  continueText: {
    color: "#FFFFFF",
    fontSize: 16,
    fontWeight: "700",
  },
  skipNote: {
    fontSize: 12,
    textAlign: "center",
  },
});
