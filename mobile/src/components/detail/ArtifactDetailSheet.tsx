/**
 * LAYERS - Artifact Detail Sheet
 * ====================================
 * Shows artifact detail when user taps a marker on the map.
 *
 * STATES:
 *   1. LOADING  — Fetching from backend
 *   2. LOCKED   — Too far away (shows distance + "Walk closer!")
 *   3. PASSCODE — Within 50m but needs code entry
 *   4. TIME_LOCKED — Time capsule / time window lock
 *   5. UNLOCKED — Content revealed! (Letter, Notebook, etc.)
 *
 * FLOW:
 *   Tap marker → sheet slides up → fetch detail from backend
 *   → If locked: show distance + lock reason
 *   → If within 50m: show "Unlock" button → tap → UnlockAnimation → content
 *   → If passcode: show code input → verify → UnlockAnimation → content
 *
 * CONNECTS TO:
 *   GET  /api/v1/artifacts/{id}?lat=X&lng=Y
 *   POST /api/v1/artifacts/{id}/unlock?passcode=X&lat=X&lng=Y
 *   POST /api/v1/artifacts/{id}/reply
 */

import React, { useState, useRef, useEffect, useCallback, memo } from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  TextInput,
  ScrollView,
  Animated,
  Platform,
  Dimensions,
  ActivityIndicator,
  KeyboardAvoidingView,
} from "react-native";
import * as Haptics from "expo-haptics";

import UnlockAnimation from "./UnlockAnimation";
import ArtifactContent from "./ArtifactContent";
import { MARKER_CONFIGS } from "../../types/artifact";
import { Colors } from "../../constants/colors";

const { height: SCREEN_HEIGHT } = Dimensions.get("window");
const SHEET_HEIGHT = SCREEN_HEIGHT * 0.65;

// ============================================================
// TYPES
// ============================================================

export interface ArtifactDetailData {
  id: string;
  content_type: string;
  layer: string;
  visibility: string;
  latitude: number;
  longitude: number;
  distance_meters?: number;
  is_locked: boolean;
  lock_reason?: string;
  payload?: Record<string, any>;
  view_count: number;
  reply_count: number;
  save_count: number;
  creator_username?: string;
  created_at: string;
}

interface Props {
  visible: boolean;
  data: ArtifactDetailData | null;
  isLoading: boolean;
  onClose: () => void;
  onUnlockPasscode: (passcode: string) => Promise<boolean>;
  onReply: (content: string) => Promise<void>;
  isShadow: boolean;
}

// ============================================================
// COMPONENT
// ============================================================

function ArtifactDetailSheetComponent({
  visible,
  data,
  isLoading,
  onClose,
  onUnlockPasscode,
  onReply,
  isShadow,
}: Props) {
  // States
  const [showUnlockAnim, setShowUnlockAnim] = useState(false);
  const [isUnlocked, setIsUnlocked] = useState(false);
  const [passcodeInput, setPasscodeInput] = useState("");
  const [passcodeError, setPasscodeError] = useState<string | null>(null);
  const [isVerifying, setIsVerifying] = useState(false);
  const [replyText, setReplyText] = useState("");
  const [replyMode, setReplyMode] = useState(false);
  const [isSendingReply, setIsSendingReply] = useState(false);

  // Animation
  const slideAnim = useRef(new Animated.Value(SHEET_HEIGHT)).current;
  const backdropOpacity = useRef(new Animated.Value(0)).current;

  // Theme
  const colors = Colors[isShadow ? "shadow" : "light"];
  const accent = isShadow ? "#8B5CF6" : "#3B82F6";
  const bgColor = isShadow ? "#1A1025" : "#FFFFFF";
  const subtextColor = isShadow ? "#9CA3AF" : "#6B7280";
  const inputBg = isShadow ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.04)";

  // Content type config
  const typeConfig = data
    ? MARKER_CONFIGS[data.content_type as keyof typeof MARKER_CONFIGS] ||
      MARKER_CONFIGS.LETTER
    : MARKER_CONFIGS.LETTER;
  const emoji = isShadow ? typeConfig.shadowEmoji : typeConfig.emoji;

  // ========================================================
  // ANIMATION
  // ========================================================

  useEffect(() => {
    if (visible) {
      setIsUnlocked(false);
      setShowUnlockAnim(false);
      setPasscodeInput("");
      setPasscodeError(null);
      setReplyText("");
      setReplyMode(false);

      Animated.parallel([
        Animated.spring(slideAnim, {
          toValue: 0,
          friction: 8,
          tension: 65,
          useNativeDriver: true,
        }),
        Animated.timing(backdropOpacity, {
          toValue: 1,
          duration: 300,
          useNativeDriver: true,
        }),
      ]).start();
    } else {
      Animated.parallel([
        Animated.timing(slideAnim, {
          toValue: SHEET_HEIGHT,
          duration: 250,
          useNativeDriver: true,
        }),
        Animated.timing(backdropOpacity, {
          toValue: 0,
          duration: 250,
          useNativeDriver: true,
        }),
      ]).start();
    }
  }, [visible]);

  // Auto-detect if already unlocked
  useEffect(() => {
    if (data && !data.is_locked && data.payload) {
      setIsUnlocked(true);
    }
  }, [data]);

  // ========================================================
  // HANDLERS
  // ========================================================

  const handleUnlock = useCallback(() => {
    if (!data) return;
    setShowUnlockAnim(true);
  }, [data]);

  const handleUnlockAnimComplete = useCallback(() => {
    setShowUnlockAnim(false);
    setIsUnlocked(true);
  }, []);

  const handlePasscodeSubmit = useCallback(async () => {
    if (!passcodeInput.trim()) return;
    setIsVerifying(true);
    setPasscodeError(null);

    try {
      const success = await onUnlockPasscode(passcodeInput);
      if (success) {
        setShowUnlockAnim(true);
      } else {
        setPasscodeError("Wrong passcode! Try again.");
        if (Platform.OS !== "web") {
          Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
        }
      }
    } catch (err: any) {
      setPasscodeError(err.message || "Failed to verify");
    } finally {
      setIsVerifying(false);
    }
  }, [passcodeInput, onUnlockPasscode]);

  const handleSendReply = useCallback(async () => {
    if (!replyText.trim()) return;
    setIsSendingReply(true);
    try {
      await onReply(replyText.trim());
      setReplyText("");
      setReplyMode(false);
      if (Platform.OS !== "web") {
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      }
    } catch {
      // Error handled upstream
    } finally {
      setIsSendingReply(false);
    }
  }, [replyText, onReply]);

  // ========================================================
  // RENDER HELPERS
  // ========================================================

  const renderLockedState = () => {
    if (!data) return null;
    const distance = data.distance_meters;
    const reason = data.lock_reason;

    // Distance lock
    if (reason === "distance" && distance) {
      const distStr =
        distance >= 1000
          ? `${(distance / 1000).toFixed(1)}km`
          : `${Math.round(distance)}m`;

      return (
        <View style={styles.lockedContainer}>
          <Text style={styles.lockedEmoji}>🔒</Text>
          <Text style={[styles.lockedTitle, { color: colors.text }]}>
            Geo-Locked
          </Text>
          <Text style={[styles.lockedDistance, { color: accent }]}>
            {distStr} away
          </Text>
          <View style={[styles.distanceBar, { backgroundColor: inputBg }]}>
            <View
              style={[
                styles.distanceFill,
                {
                  backgroundColor: accent,
                  width: `${Math.max(5, Math.min(95, (1 - distance / 500) * 100))}%`,
                },
              ]}
            />
          </View>
          <Text style={[styles.lockedHint, { color: subtextColor }]}>
            Walk within 50m to unlock this {typeConfig.label.toLowerCase()}
          </Text>

          {/* Walking direction hint */}
          <View style={[styles.walkHint, { backgroundColor: accent + "15" }]}>
            <Text style={[styles.walkHintText, { color: accent }]}>
              🚶 Walk closer to discover what's here!
            </Text>
          </View>
        </View>
      );
    }

    // Passcode lock (within 50m but needs code)
    if (reason === "passcode") {
      return (
        <View style={styles.lockedContainer}>
          <Text style={styles.lockedEmoji}>🔐</Text>
          <Text style={[styles.lockedTitle, { color: colors.text }]}>
            Passcode Required
          </Text>
          <Text style={[styles.lockedHint, { color: subtextColor }]}>
            This {typeConfig.label.toLowerCase()} is protected. Enter the code
            to unlock.
          </Text>

          <View style={styles.passcodeRow}>
            <TextInput
              style={[
                styles.passcodeInput,
                {
                  backgroundColor: inputBg,
                  color: colors.text,
                  borderColor: passcodeError ? "#EF4444" : accent + "40",
                },
              ]}
              value={passcodeInput}
              onChangeText={(t) => {
                setPasscodeInput(t);
                setPasscodeError(null);
              }}
              placeholder="Enter passcode..."
              placeholderTextColor={subtextColor}
              autoCapitalize="none"
              autoCorrect={false}
              maxLength={32}
              returnKeyType="go"
              onSubmitEditing={handlePasscodeSubmit}
            />
            <TouchableOpacity
              style={[styles.passcodeBtn, { backgroundColor: accent }]}
              onPress={handlePasscodeSubmit}
              disabled={isVerifying || !passcodeInput.trim()}
              activeOpacity={0.7}
            >
              <Text style={styles.passcodeBtnText}>
                {isVerifying ? "..." : "🔑"}
              </Text>
            </TouchableOpacity>
          </View>

          {passcodeError && (
            <Text style={styles.errorText}>{passcodeError}</Text>
          )}
        </View>
      );
    }

    // Time lock
    return (
      <View style={styles.lockedContainer}>
        <Text style={styles.lockedEmoji}>⏰</Text>
        <Text style={[styles.lockedTitle, { color: colors.text }]}>
          Time Locked
        </Text>
        <Text style={[styles.lockedHint, { color: subtextColor }]}>
          {reason || "This artifact is locked by time"}
        </Text>
      </View>
    );
  };

  const renderUnlockedState = () => {
    if (!data || !data.payload) return null;

    return (
      <View>
        <ArtifactContent
          contentType={data.content_type}
          payload={data.payload}
          isShadow={isShadow}
          creatorUsername={data.creator_username}
          createdAt={data.created_at}
          viewCount={data.view_count}
          replyCount={data.reply_count}
        />

        {/* Reply section */}
        {!replyMode ? (
          <TouchableOpacity
            style={[styles.replyBtn, { borderColor: accent + "40" }]}
            onPress={() => setReplyMode(true)}
            activeOpacity={0.7}
          >
            <Text style={[styles.replyBtnText, { color: accent }]}>
              ✉️ Reply via Slow Mail
            </Text>
            <Text style={[styles.replyHint, { color: subtextColor }]}>
              Delivered in 6-12 hours
            </Text>
          </TouchableOpacity>
        ) : (
          <View style={styles.replyForm}>
            <TextInput
              style={[
                styles.replyInput,
                {
                  backgroundColor: inputBg,
                  color: colors.text,
                  borderColor: accent + "30",
                },
              ]}
              value={replyText}
              onChangeText={setReplyText}
              placeholder="Write your reply..."
              placeholderTextColor={subtextColor}
              multiline
              maxLength={1000}
              autoFocus
            />
            <View style={styles.replyActions}>
              <TouchableOpacity onPress={() => setReplyMode(false)}>
                <Text style={[styles.replyCancelText, { color: subtextColor }]}>
                  Cancel
                </Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[
                  styles.replySendBtn,
                  {
                    backgroundColor: replyText.trim()
                      ? accent
                      : subtextColor + "40",
                  },
                ]}
                onPress={handleSendReply}
                disabled={!replyText.trim() || isSendingReply}
              >
                <Text style={styles.replySendText}>
                  {isSendingReply ? "Sending..." : "✉️ Send"}
                </Text>
              </TouchableOpacity>
            </View>
          </View>
        )}
      </View>
    );
  };

  if (!visible) return null;

  return (
    <View style={StyleSheet.absoluteFill}>
      {/* Backdrop */}
      <Animated.View style={[styles.backdrop, { opacity: backdropOpacity }]}>
        <TouchableOpacity
          style={StyleSheet.absoluteFill}
          onPress={onClose}
          activeOpacity={1}
        />
      </Animated.View>

      {/* Sheet */}
      <Animated.View
        style={[
          styles.sheet,
          {
            backgroundColor: bgColor,
            transform: [{ translateY: slideAnim }],
            height: SHEET_HEIGHT,
          },
        ]}
      >
        <KeyboardAvoidingView
          behavior={Platform.OS === "ios" ? "padding" : undefined}
          style={{ flex: 1 }}
        >
          {/* Handle */}
          <View style={styles.handleContainer}>
            <View
              style={[
                styles.handle,
                { backgroundColor: isShadow ? "#4B5563" : "#D1D5DB" },
              ]}
            />
          </View>

          {/* Header */}
          <View style={styles.header}>
            <TouchableOpacity onPress={onClose}>
              <Text style={[styles.closeText, { color: subtextColor }]}>
                Close
              </Text>
            </TouchableOpacity>
            <View style={styles.headerCenter}>
              <Text style={styles.headerEmoji}>{emoji}</Text>
              <Text style={[styles.headerTitle, { color: colors.text }]}>
                {typeConfig.label}
              </Text>
              {data && (
                <View
                  style={[
                    styles.layerBadge,
                    {
                      backgroundColor:
                        data.layer === "SHADOW"
                          ? "#8B5CF6" + "20"
                          : "#3B82F6" + "20",
                    },
                  ]}
                >
                  <Text style={styles.layerBadgeText}>
                    {data.layer === "SHADOW" ? "🌙" : "☀️"}
                  </Text>
                </View>
              )}
            </View>
            <View style={{ width: 40 }} />
          </View>

          <ScrollView
            style={styles.scrollView}
            contentContainerStyle={styles.scrollContent}
            showsVerticalScrollIndicator={false}
            keyboardShouldPersistTaps="handled"
          >
            {/* Loading */}
            {isLoading && (
              <View style={styles.loadingContainer}>
                <ActivityIndicator color={accent} size="large" />
                <Text style={[styles.loadingText, { color: subtextColor }]}>
                  Checking proximity...
                </Text>
              </View>
            )}

            {/* Unlock Animation */}
            {showUnlockAnim && (
              <UnlockAnimation
                isUnlocking={showUnlockAnim}
                onComplete={handleUnlockAnimComplete}
                isShadow={isShadow}
              />
            )}

            {/* Content based on state */}
            {!isLoading && !showUnlockAnim && data && (
              <>
                {data.is_locked && !isUnlocked ? renderLockedState() : null}

                {/* Unlock button for geo-within-range but not yet animated */}
                {data.is_locked &&
                  !isUnlocked &&
                  data.lock_reason === "distance" &&
                  data.distance_meters &&
                  data.distance_meters <= 50 && (
                    <TouchableOpacity
                      style={[styles.unlockBtn, { backgroundColor: accent }]}
                      onPress={handleUnlock}
                      activeOpacity={0.8}
                    >
                      <Text style={styles.unlockBtnText}>🔓 Unlock Now!</Text>
                    </TouchableOpacity>
                  )}

                {/* Already unlocked content */}
                {(isUnlocked || (!data.is_locked && data.payload)) &&
                  renderUnlockedState()}
              </>
            )}
          </ScrollView>
        </KeyboardAvoidingView>
      </Animated.View>
    </View>
  );
}

// ============================================================
// STYLES
// ============================================================

const styles = StyleSheet.create({
  backdrop: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: "rgba(0,0,0,0.5)",
    zIndex: 90,
  },
  sheet: {
    position: "absolute",
    bottom: 0,
    left: 0,
    right: 0,
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    zIndex: 100,
    ...Platform.select({
      ios: {
        shadowColor: "#000",
        shadowOffset: { width: 0, height: -4 },
        shadowOpacity: 0.15,
        shadowRadius: 12,
      },
      android: { elevation: 16 },
    }),
  },
  handleContainer: { alignItems: "center", paddingTop: 10, paddingBottom: 4 },
  handle: { width: 36, height: 4, borderRadius: 2 },

  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 20,
    paddingVertical: 10,
  },
  closeText: { fontSize: 15, fontWeight: "500" },
  headerCenter: { flexDirection: "row", alignItems: "center", gap: 8 },
  headerEmoji: { fontSize: 22 },
  headerTitle: { fontSize: 17, fontWeight: "700" },
  layerBadge: { paddingHorizontal: 6, paddingVertical: 2, borderRadius: 8 },
  layerBadgeText: { fontSize: 12 },

  scrollView: { flex: 1 },
  scrollContent: { paddingHorizontal: 20, paddingBottom: 30 },

  // Loading
  loadingContainer: { alignItems: "center", paddingVertical: 40 },
  loadingText: { fontSize: 14, marginTop: 12 },

  // Locked state
  lockedContainer: { alignItems: "center", paddingVertical: 20 },
  lockedEmoji: { fontSize: 48, marginBottom: 12 },
  lockedTitle: { fontSize: 20, fontWeight: "800", marginBottom: 4 },
  lockedDistance: { fontSize: 28, fontWeight: "900", marginBottom: 12 },
  lockedHint: {
    fontSize: 14,
    textAlign: "center",
    marginBottom: 16,
    paddingHorizontal: 10,
  },
  distanceBar: {
    width: "80%",
    height: 6,
    borderRadius: 3,
    marginBottom: 16,
    overflow: "hidden",
  },
  distanceFill: { height: "100%", borderRadius: 3 },
  walkHint: {
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: 12,
    marginTop: 4,
  },
  walkHintText: { fontSize: 14, fontWeight: "600", textAlign: "center" },

  // Passcode
  passcodeRow: { flexDirection: "row", gap: 10, marginTop: 16, width: "85%" },
  passcodeInput: {
    flex: 1,
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: Platform.OS === "ios" ? 12 : 10,
    fontSize: 16,
  },
  passcodeBtn: {
    width: 48,
    height: 48,
    borderRadius: 12,
    alignItems: "center",
    justifyContent: "center",
  },
  passcodeBtnText: { fontSize: 20 },
  errorText: {
    color: "#EF4444",
    fontSize: 13,
    marginTop: 8,
    fontWeight: "500",
  },

  // Unlock button
  unlockBtn: {
    paddingVertical: 16,
    borderRadius: 24,
    alignItems: "center",
    marginVertical: 16,
  },
  unlockBtnText: { color: "#FFF", fontSize: 17, fontWeight: "800" },

  // Reply
  replyBtn: {
    borderWidth: 1,
    borderRadius: 14,
    padding: 16,
    alignItems: "center",
    marginTop: 12,
    borderStyle: "dashed",
  },
  replyBtnText: { fontSize: 15, fontWeight: "700" },
  replyHint: { fontSize: 11, marginTop: 2 },
  replyForm: { marginTop: 12 },
  replyInput: {
    borderWidth: 1,
    borderRadius: 14,
    padding: 14,
    fontSize: 15,
    minHeight: 80,
    maxHeight: 120,
  },
  replyActions: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginTop: 10,
  },
  replyCancelText: { fontSize: 14, fontWeight: "500" },
  replySendBtn: {
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 20,
  },
  replySendText: { color: "#FFF", fontSize: 14, fontWeight: "700" },
});

export default memo(ArtifactDetailSheetComponent);
