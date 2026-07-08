// ===========================================
// LAYERS Root Navigator
// Switches between Auth, Onboarding and Main based on auth state
//   not authenticated            → AuthNavigator
//   authenticated + no onboarding → OnboardingNavigator (once per device)
//   authenticated + onboarded     → MainNavigator
// ===========================================

import React, { useEffect } from "react";
import { ActivityIndicator, View, StyleSheet, Text } from "react-native";
import { useAuthStore } from "../store/authStore";
import { useOnboardingStore } from "../store/onboardingStore";
import AuthNavigator from "./AuthNavigator";
import MainNavigator from "./MainNavigator";
import OnboardingNavigator from "./OnboardingNavigator";
import { Colors } from "../constants/colors";
import { useNotifications } from "../hooks/useNotifications";

export default function RootNavigator() {
  const { isAuthenticated, isLoading, loadStoredAuth, layer } = useAuthStore();
  const { isHydrated, hasCompletedOnboarding, hydrate } = useOnboardingStore();
  const { expoPushToken } = useNotifications();
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];

  // Load stored auth on app start
  useEffect(() => {
    loadStoredAuth();
    hydrate();
  }, []);

  // Loading screen while checking auth + hydrating onboarding flags
  if (isLoading || !isHydrated) {
    return (
      <View style={[styles.loading, { backgroundColor: colors.background }]}>
        <Text style={styles.loadingLogo}>🌆</Text>
        <Text style={[styles.loadingTitle, { color: colors.text }]}>
          LAYERS
        </Text>
        <ActivityIndicator
          size="large"
          color={colors.primary}
          style={styles.spinner}
        />
        <Text style={[styles.loadingText, { color: colors.textSecondary }]}>
          Loading your city's layers...
        </Text>
      </View>
    );
  }

  if (!isAuthenticated) {
    return <AuthNavigator />;
  }

  if (!hasCompletedOnboarding) {
    return <OnboardingNavigator />;
  }

  return <MainNavigator />;
}

const styles = StyleSheet.create({
  loading: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
  },
  loadingLogo: {
    fontSize: 80,
    marginBottom: 16,
  },
  loadingTitle: {
    fontSize: 36,
    fontWeight: "bold",
    letterSpacing: 4,
    marginBottom: 32,
  },
  spinner: {
    marginBottom: 16,
  },
  loadingText: {
    fontSize: 14,
  },
});
