/**
 * LAYERS — EmptyChat Components
 * =============================================
 * Empty states for the ChatListScreen and inside ChatRoomScreen.
 */

import React from "react";
import { View, Text, StyleSheet } from "react-native";
import { Colors } from "../../constants/colors";
import { useAuthStore } from "../../store/authStore";

// ============================================================
// EmptyChatList — shown on ChatListScreen when no rooms
// ============================================================

export function EmptyChatList() {
  const layer = useAuthStore((s) => s.layer);
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];

  return (
    <View style={styles.container}>
      <Text style={styles.icon}>💬</Text>
      <Text style={[styles.title, { color: colors.text }]}>No chats yet</Text>
      <Text style={[styles.message, { color: colors.textSecondary }]}>
        Real-time chat unlocks when you and someone else become CONNECTED. Send
        Slow Mail and reply to letters to grow connections.
      </Text>
    </View>
  );
}

// ============================================================
// EmptyChatRoom — shown inside a ChatRoomScreen with no messages
// ============================================================

export function EmptyChatRoom() {
  const layer = useAuthStore((s) => s.layer);
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];

  return (
    <View style={styles.container}>
      <Text style={styles.icon}>✨</Text>
      <Text style={[styles.title, { color: colors.text }]}>Say hello</Text>
      <Text style={[styles.message, { color: colors.textSecondary }]}>
        This conversation is just beginning.
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 40,
    paddingBottom: 60,
  },
  icon: {
    fontSize: 56,
    marginBottom: 14,
  },
  title: {
    fontSize: 19,
    fontWeight: "600",
    marginBottom: 8,
    textAlign: "center",
  },
  message: {
    fontSize: 14,
    lineHeight: 21,
    textAlign: "center",
  },
});

export default EmptyChatList;
