/**
 * LAYERS — MessageBubble Component
 * =================================================
 * A single chat bubble. Sent messages right-aligned in primary color,
 * received left-aligned in surface color.
 *
 * PATTERN: React.memo, same as LetterCard, ConnectionCard, ArtifactMarker.
 * Uses Colors[layer] theming for Light/Shadow modes.
 */

import React from "react";
import { View, Text, StyleSheet, ActivityIndicator } from "react-native";
import { Colors } from "../../constants/colors";
import { useAuthStore } from "../../store/authStore";
import { ChatMessageWithStatus } from "../../types/chat";

// ============================================================
// HELPERS
// ============================================================

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

// ============================================================
// COMPONENT
// ============================================================

interface MessageBubbleProps {
  message: ChatMessageWithStatus;
  isMine: boolean;
  /** Show the time label below this bubble. Set false for grouped messages. */
  showTime?: boolean;
}

export const MessageBubble = React.memo(function MessageBubble({
  message,
  isMine,
  showTime = true,
}: MessageBubbleProps) {
  const layer = useAuthStore((s) => s.layer);
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];

  const bubbleBg = isMine ? colors.primary : colors.surface;
  const textColor = isMine ? "#FFFFFF" : colors.text;
  const subTextColor = isMine ? "rgba(255,255,255,0.7)" : colors.textSecondary;

  const isSending = message.status === "sending";
  const isFailed = message.status === "failed";

  return (
    <View style={[styles.row, isMine ? styles.rowRight : styles.rowLeft]}>
      <View
        style={[
          styles.bubble,
          isMine ? styles.bubbleMine : styles.bubbleTheirs,
          { backgroundColor: bubbleBg },
          isFailed && { opacity: 0.6 },
        ]}
      >
        <Text style={[styles.text, { color: textColor }]}>
          {message.content}
        </Text>

        {showTime && (
          <View style={styles.metaRow}>
            <Text style={[styles.time, { color: subTextColor }]}>
              {formatTime(message.created_at)}
            </Text>
            {isMine && isSending && (
              <ActivityIndicator
                size="small"
                color={subTextColor}
                style={styles.statusIcon}
              />
            )}
            {isMine && isFailed && (
              <Text style={[styles.failedIcon, { color: "#FF6B6B" }]}>⚠️</Text>
            )}
            {isMine && message.status === "sent" && (
              <Text style={[styles.statusIcon, { color: subTextColor }]}>
                ✓
              </Text>
            )}
          </View>
        )}
      </View>
    </View>
  );
});

MessageBubble.displayName = "MessageBubble";

// ============================================================
// STYLES
// ============================================================

const styles = StyleSheet.create({
  row: {
    flexDirection: "row",
    paddingHorizontal: 12,
    marginVertical: 2,
  },
  rowLeft: {
    justifyContent: "flex-start",
  },
  rowRight: {
    justifyContent: "flex-end",
  },
  bubble: {
    maxWidth: "78%",
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 18,
  },
  bubbleMine: {
    borderBottomRightRadius: 4,
  },
  bubbleTheirs: {
    borderBottomLeftRadius: 4,
  },
  text: {
    fontSize: 15,
    lineHeight: 20,
  },
  metaRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "flex-end",
    marginTop: 4,
    gap: 4,
  },
  time: {
    fontSize: 10,
  },
  statusIcon: {
    fontSize: 11,
    marginLeft: 2,
  },
  failedIcon: {
    fontSize: 12,
    marginLeft: 2,
  },
});

export default MessageBubble;
