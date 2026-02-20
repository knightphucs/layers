// ===========================================
// Full screen loading overlay
// ===========================================

import React from "react";
import { View, Text, StyleSheet, ActivityIndicator, Modal } from "react-native";
import { Colors } from "../constants/colors";
import { useAuthStore } from "../store/authStore";

interface LoadingProps {
  visible?: boolean;
  message?: string;
  overlay?: boolean;
}

export default function Loading({
  visible = true,
  message = "Loading...",
  overlay = false,
}: LoadingProps) {
  const layer = useAuthStore((state) => state.layer);
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];

  const content = (
    <View
      style={[
        styles.container,
        { backgroundColor: overlay ? "rgba(0,0,0,0.5)" : colors.background },
      ]}
    >
      <View style={[styles.card, { backgroundColor: colors.surface }]}>
        <Text style={styles.logo}>🌆</Text>
        <ActivityIndicator size="large" color={colors.primary} />
        <Text style={[styles.message, { color: colors.textSecondary }]}>
          {message}
        </Text>
      </View>
    </View>
  );

  if (overlay) {
    return (
      <Modal visible={visible} transparent animationType="fade">
        {content}
      </Modal>
    );
  }

  if (!visible) return null;

  return content;
}

// Inline loading indicator (not full screen)
export function LoadingInline({
  size = "small",
}: {
  size?: "small" | "large";
}) {
  const layer = useAuthStore((state) => state.layer);
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];

  return (
    <View style={styles.inline}>
      <ActivityIndicator size={size} color={colors.primary} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
  },
  card: {
    padding: 32,
    borderRadius: 20,
    alignItems: "center",
    minWidth: 150,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.15,
    shadowRadius: 12,
    elevation: 8,
  },
  logo: {
    fontSize: 40,
    marginBottom: 16,
  },
  message: {
    marginTop: 16,
    fontSize: 14,
  },
  inline: {
    padding: 20,
    alignItems: "center",
    justifyContent: "center",
  },
});
