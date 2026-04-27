/**
 * LAYERS — EmptyConnections Component
 * ==========================================
 * Empty state for the Connections screen.
 */

import React from "react";
import { View, Text, StyleSheet } from "react-native";
import { Colors } from "../../constants/colors";
import { useAuthStore } from "../../store/authStore";
import { ConnectionLevel } from "../../types/connections";

// ============================================================
// EMPTY STATES PER FILTER
// ============================================================

const EMPTY_STATES: Record<
  ConnectionLevel | "all",
  { icon: string; title: string; message: string }
> = {
  all: {
    icon: "🤝",
    title: "No connections yet",
    message:
      "Reply to letters around the city to start connecting with other explorers. Every exchange brings you closer.",
  },
  STRANGER: {
    icon: "👤",
    title: "No strangers",
    message:
      "Anonymous connections appear here when you first exchange letters with someone new.",
  },
  SIGNAL: {
    icon: "📡",
    title: "No signals yet",
    message:
      "After 5 exchanged letters with the same person, their identity is revealed and you'll see them here.",
  },
  CONNECTED: {
    icon: "✨",
    title: "No connections yet",
    message:
      "When both of you accept a connection request, realtime chat opens up and you'll appear here together.",
  },
};

// ============================================================
// COMPONENT
// ============================================================

interface EmptyConnectionsProps {
  filter: ConnectionLevel | "all";
}

export default function EmptyConnections({ filter }: EmptyConnectionsProps) {
  const layer = useAuthStore((s) => s.layer);
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];
  const content = EMPTY_STATES[filter];

  return (
    <View style={styles.container}>
      <Text style={styles.icon}>{content.icon}</Text>
      <Text style={[styles.title, { color: colors.text }]}>
        {content.title}
      </Text>
      <Text style={[styles.message, { color: colors.textSecondary }]}>
        {content.message}
      </Text>
    </View>
  );
}

// ============================================================
// STYLES
// ============================================================

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 40,
    paddingBottom: 80,
    paddingTop: 40,
  },
  icon: {
    fontSize: 56,
    marginBottom: 16,
  },
  title: {
    fontSize: 20,
    fontWeight: "600",
    marginBottom: 10,
    textAlign: "center",
  },
  message: {
    fontSize: 14,
    lineHeight: 22,
    textAlign: "center",
  },
});
