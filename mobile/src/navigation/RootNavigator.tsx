// ===========================================
// LAYERS Root Navigator
// Switches between Auth and Main based on auth state
// ===========================================

import React, { useEffect } from "react";
import { ActivityIndicator, View, StyleSheet, Text } from "react-native";
import { useAuthStore } from "../store/authStore";
import AuthNavigator from "./AuthNavigator";
import MainNavigator from "./MainNavigator";
import { Colors } from "../constants/colors";

export default function RootNavigator() {
  const { isAuthenticated, isLoading, loadStoredAuth, layer } = useAuthStore();
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];

  // Load stored auth on app start
  useEffect(() => {
    loadStoredAuth();
  }, []);

  // Loading screen while checking auth
  if (isLoading) {
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

  return isAuthenticated ? <MainNavigator /> : <AuthNavigator />;
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
