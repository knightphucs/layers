// ===========================================
// Shows location permission status and errors
// ===========================================

import React from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ActivityIndicator,
  Linking,
  Platform,
} from "react-native";
import { useAuthStore } from "../store/authStore";
import { Colors } from "../constants/colors";

interface LocationStatusProps {
  isLoading: boolean;
  hasPermission: boolean;
  isPermissionDenied: boolean;
  error: string | null;
  onRetry: () => void;
  compact?: boolean;
}

export default function LocationStatus({
  isLoading,
  hasPermission,
  isPermissionDenied,
  error,
  onRetry,
  compact = false,
}: LocationStatusProps) {
  const layer = useAuthStore((state) => state.layer);
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];

  const openSettings = () => {
    if (Platform.OS === "ios") {
      Linking.openURL("app-settings:");
    } else {
      Linking.openSettings();
    }
  };

  // Loading state
  if (isLoading) {
    if (compact) {
      return (
        <View
          style={[styles.compactContainer, { backgroundColor: colors.surface }]}
        >
          <ActivityIndicator size="small" color={colors.primary} />
          <Text style={[styles.compactText, { color: colors.textSecondary }]}>
            Getting location...
          </Text>
        </View>
      );
    }

    return (
      <View style={[styles.container, { backgroundColor: colors.background }]}>
        <Text style={styles.emoji}>📍</Text>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={[styles.title, { color: colors.text }]}>
          Finding your location
        </Text>
        <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
          This may take a moment...
        </Text>
      </View>
    );
  }

  // Permission denied
  if (isPermissionDenied) {
    if (compact) {
      return (
        <TouchableOpacity
          style={[
            styles.compactContainer,
            { backgroundColor: colors.error + "20" },
          ]}
          onPress={openSettings}
        >
          <Text style={styles.compactEmoji}>🚫</Text>
          <Text style={[styles.compactText, { color: colors.error }]}>
            Location denied - Tap to enable
          </Text>
        </TouchableOpacity>
      );
    }

    return (
      <View style={[styles.container, { backgroundColor: colors.background }]}>
        <Text style={styles.emoji}>🚫</Text>
        <Text style={[styles.title, { color: colors.text }]}>
          Location Access Needed
        </Text>
        <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
          LAYERS needs your location to show nearby memories and let you explore
          the city.
        </Text>

        <View style={styles.buttonRow}>
          <TouchableOpacity
            style={[styles.button, { backgroundColor: colors.primary }]}
            onPress={onRetry}
          >
            <Text style={styles.buttonText}>Try Again</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.buttonOutline, { borderColor: colors.primary }]}
            onPress={openSettings}
          >
            <Text style={[styles.buttonOutlineText, { color: colors.primary }]}>
              Open Settings
            </Text>
          </TouchableOpacity>
        </View>
      </View>
    );
  }

  // Error state
  if (error) {
    if (compact) {
      return (
        <TouchableOpacity
          style={[
            styles.compactContainer,
            { backgroundColor: colors.warning + "20" },
          ]}
          onPress={onRetry}
        >
          <Text style={styles.compactEmoji}>⚠️</Text>
          <Text style={[styles.compactText, { color: colors.warning }]}>
            {error} - Tap to retry
          </Text>
        </TouchableOpacity>
      );
    }

    return (
      <View style={[styles.container, { backgroundColor: colors.background }]}>
        <Text style={styles.emoji}>⚠️</Text>
        <Text style={[styles.title, { color: colors.text }]}>
          Location Error
        </Text>
        <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
          {error}
        </Text>

        <TouchableOpacity
          style={[styles.button, { backgroundColor: colors.primary }]}
          onPress={onRetry}
        >
          <Text style={styles.buttonText}>Try Again</Text>
        </TouchableOpacity>
      </View>
    );
  }

  // Success state (compact only)
  if (hasPermission && compact) {
    return (
      <View
        style={[
          styles.compactContainer,
          { backgroundColor: colors.success + "20" },
        ]}
      >
        <Text style={styles.compactEmoji}>✅</Text>
        <Text style={[styles.compactText, { color: colors.success }]}>
          Location enabled
        </Text>
      </View>
    );
  }

  return null;
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    padding: 24,
  },
  emoji: {
    fontSize: 64,
    marginBottom: 24,
  },
  title: {
    fontSize: 22,
    fontWeight: "bold",
    marginBottom: 12,
    textAlign: "center",
  },
  subtitle: {
    fontSize: 15,
    textAlign: "center",
    lineHeight: 22,
    marginBottom: 32,
    paddingHorizontal: 20,
  },
  buttonRow: {
    flexDirection: "column",
    gap: 12,
    width: "100%",
    maxWidth: 280,
  },
  button: {
    paddingVertical: 14,
    paddingHorizontal: 24,
    borderRadius: 12,
    alignItems: "center",
  },
  buttonText: {
    color: "#FFFFFF",
    fontSize: 16,
    fontWeight: "600",
  },
  buttonOutline: {
    paddingVertical: 14,
    paddingHorizontal: 24,
    borderRadius: 12,
    alignItems: "center",
    borderWidth: 2,
  },
  buttonOutlineText: {
    fontSize: 16,
    fontWeight: "600",
  },

  // Compact styles
  compactContainer: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
    marginHorizontal: 16,
    marginVertical: 8,
  },
  compactEmoji: {
    fontSize: 16,
    marginRight: 8,
  },
  compactText: {
    fontSize: 13,
    fontWeight: "500",
  },
});
