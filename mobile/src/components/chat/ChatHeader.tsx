/**
 * LAYERS — ChatHeader Component
 * ==============================================
 * Top header for the chat screen.
 * Shows back button, other user's avatar+username, and live WS state.
 */

import React from "react";
import {
  View,
  Text,
  TouchableOpacity,
  Image,
  StyleSheet,
  Platform,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Colors } from "../../constants/colors";
import { useAuthStore } from "../../store/authStore";
import { WSConnectionState } from "../../types/chat";

interface ChatHeaderProps {
  username?: string | null;
  avatarUrl?: string | null;
  wsState: WSConnectionState;
  onBack: () => void;
}

const STATUS_LABEL: Record<WSConnectionState, string> = {
  idle: "",
  connecting: "Connecting…",
  connected: "Online",
  reconnecting: "Reconnecting…",
  closed: "Offline",
};

const STATUS_COLOR: Record<WSConnectionState, string> = {
  idle: "#94A3B8",
  connecting: "#F59E0B",
  connected: "#10B981",
  reconnecting: "#F59E0B",
  closed: "#EF4444",
};

export function ChatHeader({
  username,
  avatarUrl,
  wsState,
  onBack,
}: ChatHeaderProps) {
  const layer = useAuthStore((s) => s.layer);
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];

  const displayName = username || "Anonymous";
  const initial = (displayName[0] || "?").toUpperCase();

  return (
    <SafeAreaView
      edges={["top"]}
      style={[
        styles.safe,
        { backgroundColor: colors.surface, borderBottomColor: colors.border },
      ]}
    >
      <View style={styles.row}>
        <TouchableOpacity
          onPress={onBack}
          style={styles.backBtn}
          activeOpacity={0.7}
          hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
        >
          <Text style={[styles.backIcon, { color: colors.text }]}>‹</Text>
        </TouchableOpacity>

        <View style={styles.userInfo}>
          {avatarUrl ? (
            <Image source={{ uri: avatarUrl }} style={styles.avatar} />
          ) : (
            <View
              style={[
                styles.avatarPlaceholder,
                { backgroundColor: colors.primary + "20" },
              ]}
            >
              <Text style={[styles.avatarInitial, { color: colors.primary }]}>
                {initial}
              </Text>
            </View>
          )}

          <View style={styles.namesCol}>
            <Text
              style={[styles.username, { color: colors.text }]}
              numberOfLines={1}
            >
              {displayName}
            </Text>
            {STATUS_LABEL[wsState] !== "" && (
              <View style={styles.statusRow}>
                <View
                  style={[
                    styles.statusDot,
                    { backgroundColor: STATUS_COLOR[wsState] },
                  ]}
                />
                <Text
                  style={[styles.statusText, { color: colors.textSecondary }]}
                >
                  {STATUS_LABEL[wsState]}
                </Text>
              </View>
            )}
          </View>
        </View>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    borderBottomWidth: 1,
  },
  row: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 8,
    paddingVertical: Platform.OS === "ios" ? 8 : 12,
  },
  backBtn: {
    width: 36,
    height: 36,
    alignItems: "center",
    justifyContent: "center",
  },
  backIcon: {
    fontSize: 32,
    fontWeight: "300",
    marginTop: -4,
  },
  userInfo: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    marginLeft: 4,
  },
  avatar: {
    width: 36,
    height: 36,
    borderRadius: 18,
  },
  avatarPlaceholder: {
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: "center",
    justifyContent: "center",
  },
  avatarInitial: {
    fontSize: 16,
    fontWeight: "600",
  },
  namesCol: {
    flex: 1,
  },
  username: {
    fontSize: 16,
    fontWeight: "600",
  },
  statusRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    marginTop: 2,
  },
  statusDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
  },
  statusText: {
    fontSize: 11,
  },
});

export default ChatHeader;
