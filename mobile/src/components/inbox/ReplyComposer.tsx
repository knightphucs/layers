/**
 * LAYERS — ReplyComposer
 * ==========================================
 * Slow Mail reply composer — replaces the Week 5 placeholder alert.
 *
 * THE EMOTIONAL CONTRACT (from masterplan):
 *   Replies are letters, not chat. They deliver 6–12h later, and —
 *   crucially — the backend enforces Proof of Presence: you must be
 *   within 50m of the artifact to reply. Writing happens IN PERSON.
 *
 * STATES:
 *   compose  → textarea + char counter + Slow Mail notice
 *   sending  → button disabled, spinner
 *   sent     → success card with deliver_at time (+20 XP)
 *   error    → friendly proximity/GPS/moderation messages, retry allowed
 *
 * API: POST /artifacts/{id}/reply?lat&lng  (inboxService.sendReply — Week 5)
 */

import React, { useState, useCallback } from "react";
import {
  View,
  Text,
  Modal,
  TextInput,
  TouchableOpacity,
  TouchableWithoutFeedback,
  KeyboardAvoidingView,
  ActivityIndicator,
  Platform,
  StyleSheet,
} from "react-native";
import { useAuthStore } from "../../store/authStore";
import { useLocationStore } from "../../store/locationStore";
import { inboxService } from "../../services/inbox";
import { getErrorMessage } from "../../services";
import { Colors } from "../../constants/colors";
import { InboxItem } from "../../types/inbox";

const MAX_REPLY_LENGTH = 500;

type ComposerPhase = "compose" | "sending" | "sent";

interface Props {
  /** The inbox item being replied to. null = composer hidden. */
  item: InboxItem | null;
  onClose: () => void;
  /** Called after a successful send (e.g. to refresh inbox stats). */
  onSent?: () => void;
}

export default function ReplyComposer({ item, onClose, onSent }: Props) {
  const { layer } = useAuthStore();
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];
  const { currentLocation, lastKnownLocation, getCurrentLocation } =
    useLocationStore();

  const [content, setContent] = useState("");
  const [phase, setPhase] = useState<ComposerPhase>("compose");
  const [error, setError] = useState<string | null>(null);
  const [deliverAt, setDeliverAt] = useState<string | null>(null);

  // ========================================================
  // CLOSE — reset all local state so next open is fresh
  // ========================================================

  const handleClose = useCallback(() => {
    setContent("");
    setPhase("compose");
    setError(null);
    setDeliverAt(null);
    onClose();
  }, [onClose]);

  // ========================================================
  // SEND
  // ========================================================

  const handleSend = useCallback(async () => {
    if (!item || content.trim().length === 0) return;

    setPhase("sending");
    setError(null);

    // Fresh GPS fix — Proof of Presence deserves accuracy
    let location = currentLocation ?? lastKnownLocation;
    try {
      const fresh = await getCurrentLocation();
      if (fresh) location = fresh;
    } catch {
      // fall through to lastKnown — better a stale fix than no attempt
    }

    if (!location) {
      setError(
        "We can't find your location. Slow Mail is written in person — enable GPS and try again. 📍",
      );
      setPhase("compose");
      return;
    }

    try {
      const result = await inboxService.sendReply(
        item.artifact.id,
        content.trim(),
        location.latitude,
        location.longitude,
      );
      setDeliverAt(result.deliver_at);
      setPhase("sent");
      onSent?.();
    } catch (err: any) {
      const message = getErrorMessage(err);

      // Backend 400s we know how to translate for humans:
      if (message.toLowerCase().includes("walk within")) {
        setError(
          "You're too far away. Slow Mail is written in person — walk within 50m of where this letter lives. 🚶",
        );
      } else if (
        message.toLowerCase().includes("own artifact")
      ) {
        setError("You can't reply to your own letter. 😄");
      } else {
        setError(message || "Failed to send reply. Please try again.");
      }
      setPhase("compose");
    }
  }, [item, content, currentLocation, lastKnownLocation, getCurrentLocation, onSent]);

  if (!item) return null;

  const remaining = MAX_REPLY_LENGTH - content.length;
  const senderName = item.sender?.username || "a stranger";
  const deliverDate = deliverAt
    ? new Date(deliverAt).toLocaleString("vi-VN", {
        weekday: "long",
        hour: "2-digit",
        minute: "2-digit",
      })
    : null;

  return (
    <Modal
      visible={!!item}
      transparent
      animationType="slide"
      onRequestClose={handleClose}
      statusBarTranslucent
    >
      <TouchableWithoutFeedback onPress={handleClose}>
        <View style={styles.backdrop} />
      </TouchableWithoutFeedback>

      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        style={styles.avoider}
        pointerEvents="box-none"
      >
        <View style={[styles.card, { backgroundColor: colors.background }]}>
          {/* ================= SENT ================= */}
          {phase === "sent" ? (
            <View style={styles.sentWrap}>
              <Text style={styles.sentEmoji}>📮</Text>
              <Text style={[styles.sentTitle, { color: colors.text }]}>
                Your letter is on its way
              </Text>
              <Text style={[styles.sentBody, { color: colors.textSecondary }]}>
                {deliverDate
                  ? `It will reach ${senderName} around ${deliverDate}.`
                  : `It will reach ${senderName} in 6–12 hours.`}
                {"\n"}Good letters are worth the wait. +20 XP ✨
              </Text>
              <TouchableOpacity
                style={[styles.sendButton, { backgroundColor: colors.primary }]}
                onPress={handleClose}
                accessibilityRole="button"
                accessibilityLabel="Done"
              >
                <Text style={styles.sendText}>Done</Text>
              </TouchableOpacity>
            </View>
          ) : (
            <>
              {/* ================= COMPOSE ================= */}
              <View style={styles.headerRow}>
                <Text style={[styles.title, { color: colors.text }]}>
                  ✉️ Reply to {senderName}
                </Text>
                <TouchableOpacity
                  onPress={handleClose}
                  hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}
                  accessibilityRole="button"
                  accessibilityLabel="Cancel reply"
                >
                  <Text style={[styles.closeX, { color: colors.textSecondary }]}>
                    ✕
                  </Text>
                </TouchableOpacity>
              </View>

              <Text style={[styles.slowMailNote, { color: colors.textSecondary }]}>
                🐌 Slow Mail — your reply delivers in 6–12 hours, like a real
                letter. Write something worth the wait.
              </Text>

              <TextInput
                style={[
                  styles.input,
                  {
                    color: colors.text,
                    backgroundColor: colors.surface ?? colors.background,
                    borderColor: colors.border ?? "rgba(128,128,128,0.3)",
                  },
                ]}
                placeholder="Dear stranger..."
                placeholderTextColor={colors.textSecondary}
                multiline
                maxLength={MAX_REPLY_LENGTH}
                value={content}
                onChangeText={setContent}
                editable={phase === "compose"}
                autoFocus
                accessibilityLabel="Reply message"
              />

              <View style={styles.footerRow}>
                <Text
                  style={[
                    styles.counter,
                    { color: remaining < 50 ? "#F87171" : colors.textSecondary },
                  ]}
                >
                  {remaining}
                </Text>
              </View>

              {error && <Text style={styles.errorText}>{error}</Text>}

              <TouchableOpacity
                style={[
                  styles.sendButton,
                  {
                    backgroundColor: colors.primary,
                    opacity:
                      content.trim().length === 0 || phase === "sending"
                        ? 0.5
                        : 1,
                  },
                ]}
                onPress={handleSend}
                disabled={content.trim().length === 0 || phase === "sending"}
                accessibilityRole="button"
                accessibilityLabel="Send Slow Mail reply"
              >
                {phase === "sending" ? (
                  <ActivityIndicator color="#FFFFFF" size="small" />
                ) : (
                  <Text style={styles.sendText}>Send Slow Mail ✉️</Text>
                )}
              </TouchableOpacity>
            </>
          )}
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}

// ============================================================
// STYLES
// ============================================================

const styles = StyleSheet.create({
  backdrop: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: "rgba(0,0,0,0.55)",
  },
  avoider: {
    flex: 1,
    justifyContent: "flex-end",
  },
  card: {
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    padding: 20,
    paddingBottom: 32,
  },
  headerRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 8,
  },
  title: {
    fontSize: 18,
    fontWeight: "800",
  },
  closeX: {
    fontSize: 20,
    fontWeight: "600",
  },
  slowMailNote: {
    fontSize: 13,
    lineHeight: 19,
    marginBottom: 16,
  },
  input: {
    borderWidth: 1,
    borderRadius: 16,
    padding: 16,
    fontSize: 15,
    lineHeight: 22,
    minHeight: 140,
    textAlignVertical: "top",
  },
  footerRow: {
    flexDirection: "row",
    justifyContent: "flex-end",
    marginTop: 6,
    marginBottom: 12,
  },
  counter: {
    fontSize: 12,
    fontWeight: "600",
  },
  errorText: {
    color: "#F87171",
    fontSize: 13,
    lineHeight: 19,
    marginBottom: 12,
  },
  sendButton: {
    borderRadius: 24,
    paddingVertical: 15,
    alignItems: "center",
  },
  sendText: {
    color: "#FFFFFF",
    fontSize: 15,
    fontWeight: "700",
  },
  sentWrap: {
    alignItems: "center",
    paddingVertical: 12,
  },
  sentEmoji: {
    fontSize: 56,
    marginBottom: 12,
  },
  sentTitle: {
    fontSize: 20,
    fontWeight: "800",
    marginBottom: 8,
  },
  sentBody: {
    fontSize: 14,
    lineHeight: 22,
    textAlign: "center",
    marginBottom: 20,
  },
});
