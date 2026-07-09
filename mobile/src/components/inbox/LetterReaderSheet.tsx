/**
 * LAYERS — LetterReaderSheet
 * ==========================================
 * The real letter-reading experience — replaces the Alert.alert
 * placeholder from Week 5 ("TODO Week 5 Day 3").
 *
 * DESIGN:
 *   - Modal bottom sheet (RN core Modal + Animated — NO new dependency)
 *   - "Unsealing" moment: content fades in after the sheet settles,
 *     like opening a real envelope
 *   - Handles every content type: LETTER, PHOTO (caption), VOICE (stub),
 *     PAPER_PLANE, TIME_CAPSULE
 *   - Reply button hands off to ReplyComposer (parent orchestrates)
 *
 * PATTERN: Controlled component — parent owns `item` (null = hidden),
 * same approach as ArtifactDetailSheet on the map.
 */

import React, { useRef, useEffect, useCallback } from "react";
import {
  View,
  Text,
  Modal,
  Animated,
  ScrollView,
  TouchableOpacity,
  TouchableWithoutFeedback,
  StyleSheet,
  Dimensions,
} from "react-native";
import { useAuthStore } from "../../store/authStore";
import { Colors } from "../../constants/colors";
import { InboxItem } from "../../types/inbox";

const { height: SCREEN_HEIGHT } = Dimensions.get("window");
const SHEET_HEIGHT = SCREEN_HEIGHT * 0.72;

// Content type → display config (mirrors InboxScreen's CONTENT_ICONS)
const READER_CONFIG: Record<string, { icon: string; label: string }> = {
  LETTER: { icon: "✉️", label: "Letter" },
  VOICE: { icon: "🎙️", label: "Voice Memory" },
  PHOTO: { icon: "📷", label: "Photo Memory" },
  PAPER_PLANE: { icon: "✈️", label: "Paper Plane" },
  TIME_CAPSULE: { icon: "⏰", label: "Time Capsule" },
  NOTEBOOK: { icon: "📓", label: "Shared Notebook" },
  VOUCHER: { icon: "🎁", label: "Voucher" },
};

interface Props {
  /** The inbox item to read. null = sheet hidden. */
  item: InboxItem | null;
  onClose: () => void;
  onReply: (item: InboxItem) => void;
}

export default function LetterReaderSheet({ item, onClose, onReply }: Props) {
  const { layer } = useAuthStore();
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];

  const slideAnim = useRef(new Animated.Value(SHEET_HEIGHT)).current;
  const contentFade = useRef(new Animated.Value(0)).current;

  // ========================================================
  // OPEN / CLOSE ANIMATIONS
  // ========================================================

  useEffect(() => {
    if (item) {
      // Slide sheet up, THEN fade content in — the "unsealing" beat
      slideAnim.setValue(SHEET_HEIGHT);
      contentFade.setValue(0);
      Animated.sequence([
        Animated.spring(slideAnim, {
          toValue: 0,
          friction: 9,
          tension: 60,
          useNativeDriver: true,
        }),
        Animated.timing(contentFade, {
          toValue: 1,
          duration: 350,
          useNativeDriver: true,
        }),
      ]).start();
    }
  }, [item, slideAnim, contentFade]);

  const handleClose = useCallback(() => {
    Animated.timing(slideAnim, {
      toValue: SHEET_HEIGHT,
      duration: 220,
      useNativeDriver: true,
    }).start(() => onClose());
  }, [slideAnim, onClose]);

  const handleReplyPress = useCallback(() => {
    if (!item) return;
    // Close reader first, then parent opens the composer
    Animated.timing(slideAnim, {
      toValue: SHEET_HEIGHT,
      duration: 180,
      useNativeDriver: true,
    }).start(() => onReply(item));
  }, [item, slideAnim, onReply]);

  if (!item) return null;

  const { artifact, sender } = item;
  const config = READER_CONFIG[artifact.content_type] || {
    icon: "📦",
    label: "Artifact",
  };
  const payload = artifact.payload || {};
  const bodyText: string =
    payload.text || payload.caption || payload.title || "No content available";

  const receivedDate = new Date(item.received_at).toLocaleDateString("vi-VN", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  const canReply = artifact.content_type !== "TIME_CAPSULE"; // capsules are for future-you

  return (
    <Modal
      visible={!!item}
      transparent
      animationType="fade"
      onRequestClose={handleClose}
      statusBarTranslucent
    >
      {/* Backdrop — tap to dismiss */}
      <TouchableWithoutFeedback onPress={handleClose}>
        <View style={styles.backdrop} />
      </TouchableWithoutFeedback>

      {/* Sheet */}
      <Animated.View
        style={[
          styles.sheet,
          {
            backgroundColor: colors.background,
            transform: [{ translateY: slideAnim }],
          },
        ]}
      >
        {/* Grab handle */}
        <View style={[styles.handle, { backgroundColor: colors.textSecondary }]} />

        {/* Header */}
        <View style={styles.header}>
          <Text style={styles.headerIcon}>{config.icon}</Text>
          <View style={styles.headerText}>
            <Text style={[styles.headerLabel, { color: colors.textSecondary }]}>
              {config.label}
            </Text>
            <Text style={[styles.headerSender, { color: colors.text }]}>
              {sender?.username
                ? `From ${sender.username}`
                : "From a stranger in the city"}
            </Text>
          </View>
          <TouchableOpacity
            onPress={handleClose}
            hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}
            accessibilityRole="button"
            accessibilityLabel="Close letter"
          >
            <Text style={[styles.closeX, { color: colors.textSecondary }]}>✕</Text>
          </TouchableOpacity>
        </View>

        {/* Content — fades in after sheet settles */}
        <Animated.View style={[styles.contentWrap, { opacity: contentFade }]}>
          <ScrollView
            style={styles.scroll}
            contentContainerStyle={styles.scrollContent}
            showsVerticalScrollIndicator={false}
          >
            {/* Paper-like letter body */}
            <View
              style={[
                styles.letterPaper,
                {
                  backgroundColor: colors.surface ?? colors.background,
                  borderColor: colors.border ?? "rgba(128,128,128,0.25)",
                },
              ]}
            >
              <Text style={[styles.letterText, { color: colors.text }]}>
                {bodyText}
              </Text>

              {/* VOICE stub — player lands with the Echo System post-launch */}
              {artifact.content_type === "VOICE" && (
                <Text style={[styles.voiceStub, { color: colors.textSecondary }]}>
                  🎙️ Voice playback arrives with the Echo System — coming soon.
                </Text>
              )}
            </View>

            {/* Meta footer */}
            <Text style={[styles.meta, { color: colors.textSecondary }]}>
              Received {receivedDate}
            </Text>
            {artifact.reply_count ? artifact.reply_count > 0 && (
              <Text style={[styles.meta, { color: colors.textSecondary }]}>
                💬 {artifact.reply_count}{" "}
                {artifact.reply_count === 1 ? "reply" : "replies"} so far
              </Text>
            ) : null}
          </ScrollView>
        </Animated.View>

        {/* Actions */}
        <View style={[styles.actions, { borderTopColor: colors.border ?? "rgba(128,128,128,0.2)" }]}>
          {canReply && (
            <TouchableOpacity
              style={[styles.replyButton, { backgroundColor: colors.primary }]}
              onPress={handleReplyPress}
              accessibilityRole="button"
              accessibilityLabel="Reply with Slow Mail"
            >
              <Text style={styles.replyText}>Reply ✉️  (arrives in 6–12h)</Text>
            </TouchableOpacity>
          )}
        </View>
      </Animated.View>
    </Modal>
  );
}

// ============================================================
// STYLES
// ============================================================

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.55)",
  },
  sheet: {
    position: "absolute",
    left: 0,
    right: 0,
    bottom: 0,
    height: SHEET_HEIGHT,
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    paddingTop: 8,
  },
  handle: {
    alignSelf: "center",
    width: 40,
    height: 4,
    borderRadius: 2,
    opacity: 0.4,
    marginBottom: 12,
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 20,
    marginBottom: 12,
    gap: 12,
  },
  headerIcon: {
    fontSize: 32,
  },
  headerText: {
    flex: 1,
  },
  headerLabel: {
    fontSize: 12,
    fontWeight: "600",
    textTransform: "uppercase",
    letterSpacing: 1,
  },
  headerSender: {
    fontSize: 16,
    fontWeight: "700",
    marginTop: 2,
  },
  closeX: {
    fontSize: 20,
    fontWeight: "600",
  },
  contentWrap: {
    flex: 1,
  },
  scroll: {
    flex: 1,
  },
  scrollContent: {
    paddingHorizontal: 20,
    paddingBottom: 16,
  },
  letterPaper: {
    borderWidth: 1,
    borderRadius: 16,
    padding: 20,
    marginBottom: 16,
  },
  letterText: {
    fontSize: 16,
    lineHeight: 26,
  },
  voiceStub: {
    fontSize: 13,
    fontStyle: "italic",
    marginTop: 16,
  },
  meta: {
    fontSize: 12,
    marginBottom: 4,
  },
  actions: {
    borderTopWidth: 1,
    paddingHorizontal: 20,
    paddingTop: 12,
    paddingBottom: 28,
  },
  replyButton: {
    borderRadius: 24,
    paddingVertical: 14,
    alignItems: "center",
  },
  replyText: {
    color: "#FFFFFF",
    fontSize: 15,
    fontWeight: "700",
  },
});
