/**
 * LAYERS — LetterCard Component
 * ==========================================
 * A card displaying an inbox letter with sealed/opened states.
 *
 * Visual states:
 *   SEALED (unread):  Envelope icon, bold text, accent border
 *   OPENED (read):    Letter icon, normal text, muted border
 *
 * Content type icons:
 *   LETTER        → ✉️
 *   VOICE         → 🎙️
 *   PHOTO         → 📷
 *   PAPER_PLANE   → ✈️
 *   VOUCHER       → 🎫
 *   TIME_CAPSULE  → ⏰
 *   NOTEBOOK      → 📓
 *
 * PATTERN: React.memo for performance in FlatList.
 */

import React, { useCallback, useMemo } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Animated,
} from "react-native";
import { Colors } from "../../constants/colors";
import { useAuthStore } from "../../store/authStore";
import { InboxItem } from "../../types/inbox";

// ============================================================
// CONTENT TYPE MAPPING
// ============================================================

const CONTENT_ICONS: Record<string, string> = {
  LETTER: "✉️",
  VOICE: "🎙️",
  PHOTO: "📷",
  PAPER_PLANE: "✈️",
  VOUCHER: "🎫",
  TIME_CAPSULE: "⏰",
  NOTEBOOK: "📓",
};

const CONTENT_LABELS: Record<string, string> = {
  LETTER: "Letter",
  VOICE: "Voice Memo",
  PHOTO: "Photo Memory",
  PAPER_PLANE: "Paper Plane",
  VOUCHER: "Voucher",
  TIME_CAPSULE: "Time Capsule",
  NOTEBOOK: "Notebook",
};

// ============================================================
// HELPERS
// ============================================================

function getTimeAgo(dateStr: string): string {
  const now = new Date();
  const date = new Date(dateStr);
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString("vi-VN", { day: "2-digit", month: "short" });
}

function getPreviewText(item: InboxItem): string {
  const { artifact } = item;
  const payload = artifact.payload;

  if (!payload) return "Tap to open";

  switch (artifact.content_type) {
    case "LETTER":
      return payload.text
        ? payload.text.substring(0, 80) +
            (payload.text.length > 80 ? "..." : "")
        : "A letter awaits...";
    case "VOICE":
      return `Voice memo (${payload.duration_seconds || "??"}s)`;
    case "PHOTO":
      return payload.caption || "A photo memory";
    case "PAPER_PLANE":
      return payload.text
        ? payload.text.substring(0, 80) +
            (payload.text.length > 80 ? "..." : "")
        : "A paper plane landed nearby!";
    case "VOUCHER":
      return payload.title || "A voucher for you";
    case "TIME_CAPSULE":
      if (artifact.unlock_at && new Date(artifact.unlock_at) > new Date()) {
        return `Opens on ${new Date(artifact.unlock_at).toLocaleDateString("vi-VN")}`;
      }
      return payload.text
        ? payload.text.substring(0, 80) + "..."
        : "A time capsule";
    case "NOTEBOOK":
      return payload.title || "A shared notebook";
    default:
      return "Tap to discover";
  }
}

// ============================================================
// COMPONENT
// ============================================================

interface LetterCardProps {
  item: InboxItem;
  onPress: (item: InboxItem) => void;
}

const LetterCard = React.memo(({ item, onPress }: LetterCardProps) => {
  const layer = useAuthStore((s) => s.layer);
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];

  const icon = CONTENT_ICONS[item.artifact.content_type] || "📦";
  const label = CONTENT_LABELS[item.artifact.content_type] || "Artifact";
  const preview = useMemo(() => getPreviewText(item), [item]);
  const timeAgo = useMemo(
    () => getTimeAgo(item.received_at),
    [item.received_at],
  );

  const isSealed = !item.is_read;
  const isTimeLocked =
    item.artifact.content_type === "TIME_CAPSULE" &&
    item.artifact.unlock_at &&
    new Date(item.artifact.unlock_at) > new Date();

  const handlePress = useCallback(() => {
    onPress(item);
  }, [item, onPress]);

  // Slow Mail reply indicator
  const hasReply = item.reply && !item.reply.is_delivered;
  const replyTimeLeft = hasReply
    ? (() => {
        const deliverAt = new Date(item.reply!.deliver_at);
        const now = new Date();
        const hoursLeft = Math.max(
          0,
          Math.ceil((deliverAt.getTime() - now.getTime()) / 3600000),
        );
        return hoursLeft > 0
          ? `${hoursLeft}h until delivered`
          : "Arriving soon...";
      })()
    : null;

  return (
    <TouchableOpacity
      onPress={handlePress}
      activeOpacity={0.7}
      style={[
        styles.card,
        {
          backgroundColor: isSealed ? colors.surface : colors.background,
          borderColor: isSealed ? colors.primary + "40" : colors.border,
          borderLeftColor: isSealed ? colors.primary : colors.border,
          borderLeftWidth: isSealed ? 3 : 1,
        },
      ]}
    >
      {/* Top Row: Icon + Type + Time */}
      <View style={styles.topRow}>
        <View style={styles.typeContainer}>
          <Text style={styles.icon}>{icon}</Text>
          <Text
            style={[
              styles.typeLabel,
              {
                color: isSealed ? colors.text : colors.textSecondary,
                fontWeight: isSealed ? "600" : "400",
              },
            ]}
          >
            {label}
          </Text>
          {isSealed && (
            <View
              style={[styles.unreadDot, { backgroundColor: colors.primary }]}
            />
          )}
        </View>
        <Text style={[styles.time, { color: colors.textSecondary }]}>
          {timeAgo}
        </Text>
      </View>

      {/* Sender (if known) */}
      {item.sender?.username && (
        <Text
          style={[
            styles.sender,
            {
              color: isSealed ? colors.text : colors.textSecondary,
              fontWeight: isSealed ? "600" : "500",
            },
          ]}
        >
          From {item.sender.username}
        </Text>
      )}

      {/* Preview text */}
      <Text
        style={[
          styles.preview,
          {
            color: isSealed ? colors.text : colors.textSecondary,
            fontWeight: isSealed ? "500" : "400",
          },
        ]}
        numberOfLines={2}
      >
        {isTimeLocked ? "🔒 " : ""}
        {preview}
      </Text>

      {/* Slow Mail indicator */}
      {hasReply && replyTimeLeft && (
        <View
          style={[
            styles.slowMailBadge,
            { backgroundColor: colors.primary + "15" },
          ]}
        >
          <Text style={[styles.slowMailText, { color: colors.primary }]}>
            ✉️ Reply in transit — {replyTimeLeft}
          </Text>
        </View>
      )}

      {/* Reply count */}
      {(item.artifact.reply_count ?? 0) > 0 && !hasReply && (
        <View style={styles.statsRow}>
          <Text style={[styles.statText, { color: colors.textSecondary }]}>
            💬 {item.artifact.reply_count}{" "}
            {item.artifact.reply_count === 1 ? "reply" : "replies"}
          </Text>
        </View>
      )}

      {/* Layer badge */}
      {item.artifact.layer === "SHADOW" && (
        <View
          style={[styles.layerBadge, { backgroundColor: "#7C3AED" + "20" }]}
        >
          <Text style={[styles.layerText, { color: "#7C3AED" }]}>
            🌙 Shadow
          </Text>
        </View>
      )}
    </TouchableOpacity>
  );
});

LetterCard.displayName = "LetterCard";

// ============================================================
// STYLES
// ============================================================

const styles = StyleSheet.create({
  card: {
    borderWidth: 1,
    borderRadius: 14,
    padding: 14,
    marginHorizontal: 16,
    marginBottom: 10,
  },
  topRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 6,
  },
  typeContainer: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  icon: {
    fontSize: 18,
  },
  typeLabel: {
    fontSize: 13,
  },
  unreadDot: {
    width: 7,
    height: 7,
    borderRadius: 4,
    marginLeft: 2,
  },
  time: {
    fontSize: 12,
  },
  sender: {
    fontSize: 14,
    marginBottom: 4,
  },
  preview: {
    fontSize: 14,
    lineHeight: 20,
  },
  slowMailBadge: {
    marginTop: 8,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 8,
    alignSelf: "flex-start",
  },
  slowMailText: {
    fontSize: 12,
    fontWeight: "500",
  },
  statsRow: {
    marginTop: 6,
  },
  statText: {
    fontSize: 12,
  },
  layerBadge: {
    position: "absolute",
    top: 12,
    right: 12,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
  },
  layerText: {
    fontSize: 11,
    fontWeight: "500",
  },
});

export default LetterCard;
