/**
 * LAYERS — ConnectionCard Component
 * ==========================================
 * Displays a single connection with level-aware UI.
 *
 * Visual states:
 *   STRANGER  → Anonymous avatar (?), blurred name, interaction progress
 *   SIGNAL    → Username + avatar + "Request Connection" button
 *   CONNECTED → Full profile + "Message" button
 */

import React, { useCallback, useMemo } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  Image,
  StyleSheet,
  ActivityIndicator,
} from "react-native";
import { Colors } from "../../constants/colors";
import { useAuthStore } from "../../store/authStore";
import {
  ConnectionItem,
  LEVEL_CONFIG,
  SIGNAL_THRESHOLD,
} from "../../types/connections";

// ============================================================
// HELPERS
// ============================================================

function getTimeAgo(dateStr: string | null): string {
  if (!dateStr) return "Never";
  const now = new Date();
  const date = new Date(dateStr);
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m`;
  if (diffHours < 24) return `${diffHours}h`;
  if (diffDays < 7) return `${diffDays}d`;
  return date.toLocaleDateString("vi-VN", { day: "2-digit", month: "short" });
}

// ============================================================
// COMPONENT
// ============================================================

interface ConnectionCardProps {
  connection: ConnectionItem;
  onRequestUpgrade: (id: string) => void;
  onAccept: (id: string) => void;
  onReject: (id: string) => void;
  onMessage?: (id: string) => void;
  isProcessing?: boolean;
}

const ConnectionCard = React.memo(
  ({
    connection,
    onRequestUpgrade,
    onAccept,
    onReject,
    onMessage,
    isProcessing,
  }: ConnectionCardProps) => {
    const layer = useAuthStore((s) => s.layer);
    const colors = Colors[layer.toLowerCase() as "light" | "shadow"];

    const levelConfig = LEVEL_CONFIG[connection.level];
    const isAnonymous = connection.level === "STRANGER";
    const isSignal = connection.level === "SIGNAL";
    const isConnected = connection.level === "CONNECTED";

    // Progress towards SIGNAL threshold (for STRANGER level)
    const progress = useMemo(
      () => Math.min(1, connection.interaction_count / SIGNAL_THRESHOLD),
      [connection.interaction_count],
    );

    const displayName = useMemo(() => {
      if (isAnonymous) return "Anonymous";
      return connection.other_user.username
        ? `@${connection.other_user.username}`
        : "Unknown";
    }, [isAnonymous, connection.other_user.username]);

    const initial = useMemo(() => {
      if (isAnonymous) return "?";
      return (connection.other_user.username?.[0] ?? "?").toUpperCase();
    }, [isAnonymous, connection.other_user.username]);

    // ========================================================
    // HANDLERS
    // ========================================================

    const handleRequest = useCallback(() => {
      onRequestUpgrade(connection.id);
    }, [connection.id, onRequestUpgrade]);

    const handleAccept = useCallback(() => {
      onAccept(connection.id);
    }, [connection.id, onAccept]);

    const handleReject = useCallback(() => {
      onReject(connection.id);
    }, [connection.id, onReject]);

    const handleMessage = useCallback(() => {
      onMessage?.(connection.id);
    }, [connection.id, onMessage]);

    // ========================================================
    // RENDER
    // ========================================================

    return (
      <View
        style={[
          styles.card,
          {
            backgroundColor: colors.surface,
            borderColor: colors.border,
            borderLeftColor: levelConfig.color,
            borderLeftWidth: 3,
          },
        ]}
      >
        {/* Top row: Avatar + Identity + Level badge */}
        <View style={styles.topRow}>
          <View style={styles.avatarContainer}>
            {!isAnonymous && connection.other_user.avatar_url ? (
              <Image
                source={{ uri: connection.other_user.avatar_url }}
                style={styles.avatar}
              />
            ) : (
              <View
                style={[
                  styles.avatar,
                  styles.avatarPlaceholder,
                  {
                    backgroundColor: isAnonymous
                      ? colors.border
                      : colors.primary,
                  },
                ]}
              >
                <Text style={styles.avatarInitial}>{initial}</Text>
              </View>
            )}
            {isAnonymous && (
              <View style={styles.anonymousOverlay}>
                <Text style={styles.anonymousIcon}>🔒</Text>
              </View>
            )}
          </View>

          <View style={styles.identityContainer}>
            <Text
              style={[
                styles.displayName,
                {
                  color: isAnonymous ? colors.textSecondary : colors.text,
                  fontStyle: isAnonymous ? "italic" : "normal",
                },
              ]}
            >
              {displayName}
            </Text>
            {!isAnonymous && connection.other_user.level !== null && (
              <Text style={[styles.userLevel, { color: colors.textSecondary }]}>
                Level {connection.other_user.level}
              </Text>
            )}
            <View style={styles.levelRow}>
              <Text style={styles.levelIcon}>{levelConfig.icon}</Text>
              <Text style={[styles.levelLabel, { color: levelConfig.color }]}>
                {levelConfig.label}
              </Text>
              <Text style={[styles.lastSeen, { color: colors.textSecondary }]}>
                · {getTimeAgo(connection.last_interaction_at)}
              </Text>
            </View>
          </View>
        </View>

        {/* Progress bar (only for STRANGER) */}
        {isAnonymous && (
          <View style={styles.progressSection}>
            <View style={styles.progressLabels}>
              <Text
                style={[styles.progressText, { color: colors.textSecondary }]}
              >
                {connection.interaction_count} / {SIGNAL_THRESHOLD} letters
              </Text>
              <Text
                style={[styles.progressText, { color: colors.textSecondary }]}
              >
                {SIGNAL_THRESHOLD - connection.interaction_count} until reveal
              </Text>
            </View>
            <View
              style={[styles.progressTrack, { backgroundColor: colors.border }]}
            >
              <View
                style={[
                  styles.progressFill,
                  {
                    backgroundColor: colors.primary,
                    width: `${progress * 100}%`,
                  },
                ]}
              />
            </View>
          </View>
        )}

        {/* Pending request from them (incoming) */}
        {isSignal &&
          connection.upgrade_requested_by_them &&
          !connection.upgrade_requested_by_me && (
            <View
              style={[
                styles.incomingBanner,
                { backgroundColor: colors.primary + "15" },
              ]}
            >
              <Text style={[styles.incomingText, { color: colors.primary }]}>
                💫 They want to connect with you
              </Text>
              <View style={styles.incomingActions}>
                <TouchableOpacity
                  onPress={handleReject}
                  style={[styles.actionBtn, { borderColor: colors.border }]}
                  disabled={isProcessing}
                >
                  <Text
                    style={[
                      styles.actionBtnText,
                      { color: colors.textSecondary },
                    ]}
                  >
                    Decline
                  </Text>
                </TouchableOpacity>
                <TouchableOpacity
                  onPress={handleAccept}
                  style={[
                    styles.actionBtn,
                    styles.actionBtnPrimary,
                    { backgroundColor: colors.primary },
                  ]}
                  disabled={isProcessing}
                >
                  {isProcessing ? (
                    <ActivityIndicator size="small" color="#FFFFFF" />
                  ) : (
                    <Text style={[styles.actionBtnText, { color: "#FFFFFF" }]}>
                      Accept ✨
                    </Text>
                  )}
                </TouchableOpacity>
              </View>
            </View>
          )}

        {/* Pending request I sent (outgoing) */}
        {isSignal &&
          connection.upgrade_requested_by_me &&
          !connection.upgrade_requested_by_them && (
            <View
              style={[
                styles.pendingBanner,
                { backgroundColor: colors.border + "40" },
              ]}
            >
              <Text
                style={[styles.pendingText, { color: colors.textSecondary }]}
              >
                ⏳ Request sent — waiting for their response
              </Text>
            </View>
          )}

        {/* Signal level — no pending — show Request button */}
        {isSignal &&
          !connection.upgrade_requested_by_me &&
          !connection.upgrade_requested_by_them && (
            <TouchableOpacity
              onPress={handleRequest}
              style={[
                styles.requestButton,
                {
                  backgroundColor: colors.primary + "15",
                  borderColor: colors.primary,
                },
              ]}
              disabled={isProcessing}
            >
              {isProcessing ? (
                <ActivityIndicator size="small" color={colors.primary} />
              ) : (
                <Text
                  style={[styles.requestButtonText, { color: colors.primary }]}
                >
                  ✨ Request Connection
                </Text>
              )}
            </TouchableOpacity>
          )}

        {/* Connected level — show Message button */}
        {isConnected && (
          <TouchableOpacity
            onPress={handleMessage}
            style={[styles.messageButton, { backgroundColor: colors.primary }]}
          >
            <Text style={styles.messageButtonText}>💬 Message</Text>
          </TouchableOpacity>
        )}
      </View>
    );
  },
);

ConnectionCard.displayName = "ConnectionCard";

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
    gap: 12,
  },
  avatarContainer: {
    position: "relative",
  },
  avatar: {
    width: 52,
    height: 52,
    borderRadius: 26,
  },
  avatarPlaceholder: {
    alignItems: "center",
    justifyContent: "center",
  },
  avatarInitial: {
    color: "#FFFFFF",
    fontSize: 22,
    fontWeight: "700",
  },
  anonymousOverlay: {
    position: "absolute",
    bottom: -2,
    right: -2,
    width: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: "#000",
    alignItems: "center",
    justifyContent: "center",
  },
  anonymousIcon: {
    fontSize: 11,
  },
  identityContainer: {
    flex: 1,
    justifyContent: "center",
  },
  displayName: {
    fontSize: 15,
    fontWeight: "600",
    marginBottom: 2,
  },
  userLevel: {
    fontSize: 12,
    marginBottom: 4,
  },
  levelRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
  },
  levelIcon: {
    fontSize: 13,
  },
  levelLabel: {
    fontSize: 12,
    fontWeight: "600",
  },
  lastSeen: {
    fontSize: 12,
  },
  progressSection: {
    marginTop: 12,
  },
  progressLabels: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 6,
  },
  progressText: {
    fontSize: 11,
  },
  progressTrack: {
    height: 6,
    borderRadius: 3,
    overflow: "hidden",
  },
  progressFill: {
    height: "100%",
    borderRadius: 3,
  },
  incomingBanner: {
    marginTop: 12,
    padding: 10,
    borderRadius: 10,
  },
  incomingText: {
    fontSize: 13,
    fontWeight: "600",
    marginBottom: 8,
    textAlign: "center",
  },
  incomingActions: {
    flexDirection: "row",
    gap: 8,
  },
  actionBtn: {
    flex: 1,
    paddingVertical: 8,
    borderRadius: 8,
    borderWidth: 1,
    alignItems: "center",
  },
  actionBtnPrimary: {
    borderWidth: 0,
  },
  actionBtnText: {
    fontSize: 13,
    fontWeight: "600",
  },
  pendingBanner: {
    marginTop: 12,
    padding: 10,
    borderRadius: 10,
    alignItems: "center",
  },
  pendingText: {
    fontSize: 12,
    fontWeight: "500",
  },
  requestButton: {
    marginTop: 12,
    paddingVertical: 10,
    borderRadius: 10,
    borderWidth: 1,
    alignItems: "center",
  },
  requestButtonText: {
    fontSize: 13,
    fontWeight: "600",
  },
  messageButton: {
    marginTop: 12,
    paddingVertical: 10,
    borderRadius: 10,
    alignItems: "center",
  },
  messageButtonText: {
    color: "#FFFFFF",
    fontSize: 14,
    fontWeight: "600",
  },
});

export default ConnectionCard;
