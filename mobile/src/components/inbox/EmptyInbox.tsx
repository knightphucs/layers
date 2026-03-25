/**
 * LAYERS — EmptyInbox Component (Week 5 Day 1)
 * ==========================================
 * Beautiful empty state that encourages users to explore.
 *
 * Different messages per category:
 *   all           → "Walk around to discover letters nearby"
 *   received      → "No letters yet. Leave one to start a conversation!"
 *   replies       → "Your replies will appear here"
 *   paper_planes  → "No paper planes found. Keep walking!"
 *   time_capsules → "No time capsules yet. Create one for the future!"
 */

import React from "react";
import { View, Text, StyleSheet, TouchableOpacity } from "react-native";
import { Colors } from "../../constants/colors";
import { useAuthStore } from "../../store/authStore";
import { InboxCategory } from "../../types/inbox";

// ============================================================
// EMPTY STATE CONTENT
// ============================================================

const EMPTY_STATES: Record<
  InboxCategory | "all",
  { icon: string; title: string; message: string; action?: string }
> = {
  all: {
    icon: "🗺️",
    title: "Your inbox is quiet",
    message:
      "Walk around your city to discover letters and memories left by others. Every step reveals something new.",
    action: "Open Map",
  },
  received: {
    icon: "✉️",
    title: "No letters yet",
    message:
      "Leave a memory at a place you love. When someone replies, it'll show up here.",
    action: "Drop a Memory",
  },
  replies: {
    icon: "💬",
    title: "No replies yet",
    message:
      "Replies travel by Slow Mail — they take 6-12 hours to arrive, like a real letter. Check back later!",
  },
  paper_planes: {
    icon: "✈️",
    title: "No paper planes found",
    message:
      "Paper planes land 200m-1km away from where they're thrown. Keep walking to find one!",
    action: "Throw a Paper Plane",
  },
  time_capsules: {
    icon: "⏰",
    title: "No time capsules",
    message:
      "Create a time capsule to send a message to the future. Pick a date and seal it.",
    action: "Create Time Capsule",
  },
};

// ============================================================
// COMPONENT
// ============================================================

interface EmptyInboxProps {
  category: InboxCategory | "all";
  onAction?: () => void;
}

export default function EmptyInbox({ category, onAction }: EmptyInboxProps) {
  const layer = useAuthStore((s) => s.layer);
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];
  const content = EMPTY_STATES[category];

  return (
    <View style={styles.container}>
      <Text style={styles.icon}>{content.icon}</Text>
      <Text style={[styles.title, { color: colors.text }]}>
        {content.title}
      </Text>
      <Text style={[styles.message, { color: colors.textSecondary }]}>
        {content.message}
      </Text>
      {content.action && onAction && (
        <TouchableOpacity
          onPress={onAction}
          style={[styles.actionButton, { backgroundColor: colors.primary }]}
          activeOpacity={0.8}
        >
          <Text style={styles.actionText}>{content.action}</Text>
        </TouchableOpacity>
      )}
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
    marginBottom: 24,
  },
  actionButton: {
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 12,
  },
  actionText: {
    color: "#FFFFFF",
    fontSize: 14,
    fontWeight: "600",
  },
});
