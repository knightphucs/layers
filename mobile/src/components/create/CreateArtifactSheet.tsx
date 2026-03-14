/**
 * LAYERS - Create Artifact Sheet
 * ====================================
 * The main creation flow — a bottom sheet that slides up from the map.
 * Users fill in: content type, text, privacy, layer → drop!
 *
 * FLOW:
 *   1. User taps "Drop Memory" button on map
 *   2. Sheet slides up from bottom
 *   3. Choose type (Letter, Notebook, etc.)
 *   4. Write message
 *   5. Set privacy (Public, Passcode)
 *   6. Choose layer (Light/Shadow)
 *   7. Tap "Drop!" button
 *   8. Sheet closes → DropAnimation plays → Marker appears
 *
 * CONNECTS TO:
 *   POST /api/v1/artifacts
 *   Uses current GPS location from locationStore
 *   Adds new artifact to artifactStore
 */

import React, { useState, useRef, useCallback, useEffect, memo } from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  TextInput,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
  Animated,
  Dimensions,
  Keyboard,
} from "react-native";
import * as Haptics from "expo-haptics";

// Sub-components
import ContentTypePicker, { CreatableContentType } from "./ContentTypePicker";
import PrivacySelector, { VisibilityMode } from "./PrivacySelector";

// Types from Day 1
import { MARKER_CONFIGS } from "../../types/artifact";

const { height: SCREEN_HEIGHT } = Dimensions.get("window");
const SHEET_HEIGHT = SCREEN_HEIGHT * 0.72;

// ============================================================
// TYPES
// ============================================================

interface Props {
  visible: boolean;
  onClose: () => void;
  onSubmit: (data: CreateArtifactData) => Promise<void>;
  isShadow: boolean;
  currentLayer: string;
}

export interface CreateArtifactData {
  content_type: CreatableContentType;
  payload: Record<string, any>;
  visibility: VisibilityMode;
  passcode?: string;
  target_username?: string;
  layer: string;
}

// ============================================================
// COMPONENT
// ============================================================

function CreateArtifactSheetComponent({
  visible,
  onClose,
  onSubmit,
  isShadow,
  currentLayer,
}: Props) {
  // Form state
  const [contentType, setContentType] =
    useState<CreatableContentType>("LETTER");
  const [text, setText] = useState("");
  const [visibility, setVisibility] = useState<VisibilityMode>("PUBLIC");
  const [passcode, setPasscode] = useState("");
  const [targetUsername, setTargetUsername] = useState("");
  const [selectedLayer, setSelectedLayer] = useState(currentLayer);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [charCount, setCharCount] = useState(0);

  // Animation
  const slideAnim = useRef(new Animated.Value(SHEET_HEIGHT)).current;
  const backdropOpacity = useRef(new Animated.Value(0)).current;

  // Max characters per type
  const maxChars = contentType === "LETTER" ? 2000 : 500;

  // ========================================================
  // ANIMATION: Slide up / down
  // ========================================================

  useEffect(() => {
    if (visible) {
      // Reset form
      setContentType("LETTER");
      setText("");
      setVisibility("PUBLIC");
      setPasscode("");
      setTargetUsername("");
      setSelectedLayer(currentLayer);
      setIsSubmitting(false);
      setCharCount(0);

      // Slide up
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
      // Slide down
      Keyboard.dismiss();
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

  // ========================================================
  // HANDLERS
  // ========================================================

  const handleTextChange = useCallback(
    (value: string) => {
      if (value.length <= maxChars) {
        setText(value);
        setCharCount(value.length);
      }
    },
    [maxChars],
  );

  const handleSubmit = useCallback(async () => {
    // Validation
    if (!text.trim()) {
      if (Platform.OS !== "web") {
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
      }
      return;
    }

    if (visibility === "PASSCODE" && !passcode.trim()) {
      if (Platform.OS !== "web") {
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
      }
      return;
    }

    setIsSubmitting(true);

    // Build payload based on content type
    let payload: Record<string, any> = {};

    switch (contentType) {
      case "LETTER":
        payload = { text: text.trim() };
        break;
      case "NOTEBOOK":
        payload = { pages: [text.trim()] };
        break;
      case "PHOTO":
        payload = { url: "", caption: text.trim() }; // URL from upload (Week 5)
        break;
      case "VOICE":
        payload = { url: "", duration_sec: 0, transcript: text.trim() };
        break;
    }

    try {
      await onSubmit({
        content_type: contentType,
        payload,
        visibility,
        passcode: visibility === "PASSCODE" ? passcode : undefined,
        target_username: visibility === "TARGETED" ? targetUsername : undefined,
        layer: selectedLayer,
      });

      // Haptic success
      if (Platform.OS !== "web") {
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      }
    } catch (error) {
      console.error("[CreateArtifact] Submit failed:", error);
      if (Platform.OS !== "web") {
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error);
      }
    } finally {
      setIsSubmitting(false);
    }
  }, [
    contentType,
    text,
    visibility,
    passcode,
    targetUsername,
    selectedLayer,
    onSubmit,
  ]);

  // ========================================================
  // THEME
  // ========================================================

  const accentColor = isShadow ? "#8B5CF6" : "#3B82F6";
  const bgColor = isShadow ? "#1A1025" : "#FFFFFF";
  const surfaceColor = isShadow ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.03)";
  const textColor = isShadow ? "#F3F4F6" : "#111827";
  const subtextColor = isShadow ? "#9CA3AF" : "#6B7280";
  const inputBg = isShadow ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.04)";

  // Content type config for emoji display
  const typeConfig = MARKER_CONFIGS[contentType] || MARKER_CONFIGS.LETTER;
  const currentEmoji = isShadow ? typeConfig.shadowEmoji : typeConfig.emoji;

  // Validation state
  const isValid =
    text.trim().length > 0 &&
    (visibility !== "PASSCODE" || passcode.trim().length > 0);

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
          style={styles.keyboardAvoid}
        >
          {/* Handle bar */}
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
              <Text style={[styles.cancelText, { color: subtextColor }]}>
                Cancel
              </Text>
            </TouchableOpacity>
            <View style={styles.headerCenter}>
              <Text style={styles.headerEmoji}>{currentEmoji}</Text>
              <Text style={[styles.headerTitle, { color: textColor }]}>
                {isShadow ? "Drop Shadow" : "Drop Memory"}
              </Text>
            </View>
            <View style={{ width: 50 }} />
          </View>

          <ScrollView
            style={styles.scrollView}
            contentContainerStyle={styles.scrollContent}
            showsVerticalScrollIndicator={false}
            keyboardShouldPersistTaps="handled"
          >
            {/* Content Type Picker */}
            <ContentTypePicker
              selected={contentType}
              onSelect={setContentType}
              isShadow={isShadow}
            />

            {/* Text Input */}
            <View style={styles.inputSection}>
              <Text style={[styles.sectionLabel, { color: subtextColor }]}>
                {contentType === "LETTER" ? "Your message" : "Write something"}
              </Text>
              <TextInput
                style={[
                  styles.messageInput,
                  {
                    backgroundColor: inputBg,
                    color: textColor,
                    borderColor:
                      text.length > 0 ? accentColor + "30" : "transparent",
                  },
                ]}
                value={text}
                onChangeText={handleTextChange}
                placeholder={
                  contentType === "LETTER"
                    ? isShadow
                      ? "Whisper your secret into the night..."
                      : "Leave a memory at this place..."
                    : "Start writing..."
                }
                placeholderTextColor={subtextColor}
                multiline
                maxLength={maxChars}
                textAlignVertical="top"
                autoFocus={false}
              />
              <Text
                style={[
                  styles.charCount,
                  {
                    color:
                      charCount > maxChars * 0.9 ? "#EF4444" : subtextColor,
                  },
                ]}
              >
                {charCount}/{maxChars}
              </Text>
            </View>

            {/* Privacy Selector */}
            <PrivacySelector
              selected={visibility}
              onSelect={setVisibility}
              passcode={passcode}
              onPasscodeChange={setPasscode}
              targetUsername={targetUsername}
              onTargetUsernameChange={setTargetUsername}
              isShadow={isShadow}
            />

            {/* Layer Selector */}
            <View style={styles.layerSection}>
              <Text style={[styles.sectionLabel, { color: subtextColor }]}>
                Which layer?
              </Text>
              <View style={styles.layerRow}>
                <TouchableOpacity
                  style={[
                    styles.layerOption,
                    {
                      backgroundColor:
                        selectedLayer === "LIGHT"
                          ? "rgba(59, 130, 246, 0.1)"
                          : surfaceColor,
                      borderColor:
                        selectedLayer === "LIGHT" ? "#3B82F6" : "transparent",
                    },
                  ]}
                  onPress={() => setSelectedLayer("LIGHT")}
                >
                  <Text style={styles.layerEmoji}>☀️</Text>
                  <Text
                    style={[
                      styles.layerLabel,
                      {
                        color:
                          selectedLayer === "LIGHT" ? "#3B82F6" : textColor,
                      },
                    ]}
                  >
                    Light
                  </Text>
                  <Text style={[styles.layerDesc, { color: subtextColor }]}>
                    Visible daytime
                  </Text>
                </TouchableOpacity>

                <TouchableOpacity
                  style={[
                    styles.layerOption,
                    {
                      backgroundColor:
                        selectedLayer === "SHADOW"
                          ? "rgba(139, 92, 246, 0.15)"
                          : surfaceColor,
                      borderColor:
                        selectedLayer === "SHADOW" ? "#8B5CF6" : "transparent",
                    },
                  ]}
                  onPress={() => setSelectedLayer("SHADOW")}
                >
                  <Text style={styles.layerEmoji}>🌙</Text>
                  <Text
                    style={[
                      styles.layerLabel,
                      {
                        color:
                          selectedLayer === "SHADOW" ? "#8B5CF6" : textColor,
                      },
                    ]}
                  >
                    Shadow
                  </Text>
                  <Text style={[styles.layerDesc, { color: subtextColor }]}>
                    Secrets at night
                  </Text>
                </TouchableOpacity>
              </View>
            </View>

            {/* GPS Info */}
            <View style={[styles.gpsInfo, { backgroundColor: surfaceColor }]}>
              <Text style={[styles.gpsText, { color: subtextColor }]}>
                📍 Dropping at your current location
              </Text>
              <Text style={[styles.gpsHint, { color: subtextColor }]}>
                Others must be within 50m to read this
              </Text>
            </View>
          </ScrollView>

          {/* Submit Button */}
          <View style={styles.submitContainer}>
            <TouchableOpacity
              style={[
                styles.submitBtn,
                {
                  backgroundColor: isValid
                    ? selectedLayer === "SHADOW"
                      ? "#8B5CF6"
                      : "#3B82F6"
                    : isShadow
                      ? "#374151"
                      : "#D1D5DB",
                },
              ]}
              onPress={handleSubmit}
              disabled={!isValid || isSubmitting}
              activeOpacity={0.8}
            >
              {isSubmitting ? (
                <Text style={styles.submitText}>Dropping...</Text>
              ) : (
                <Text style={styles.submitText}>
                  {currentEmoji} Drop{" "}
                  {contentType === "LETTER"
                    ? "Letter"
                    : contentType === "NOTEBOOK"
                      ? "Notebook"
                      : "Memory"}
                </Text>
              )}
            </TouchableOpacity>
          </View>
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
    backgroundColor: "rgba(0, 0, 0, 0.5)",
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
  keyboardAvoid: {
    flex: 1,
  },
  handleContainer: {
    alignItems: "center",
    paddingTop: 10,
    paddingBottom: 4,
  },
  handle: {
    width: 36,
    height: 4,
    borderRadius: 2,
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 20,
    paddingVertical: 12,
  },
  cancelText: {
    fontSize: 15,
    fontWeight: "500",
    width: 50,
  },
  headerCenter: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  headerEmoji: {
    fontSize: 22,
  },
  headerTitle: {
    fontSize: 17,
    fontWeight: "700",
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    paddingHorizontal: 20,
    paddingBottom: 20,
  },

  // Sections
  inputSection: {
    marginBottom: 16,
  },
  sectionLabel: {
    fontSize: 13,
    fontWeight: "600",
    marginBottom: 8,
    paddingHorizontal: 4,
  },
  messageInput: {
    minHeight: 100,
    maxHeight: 160,
    borderRadius: 14,
    padding: 14,
    fontSize: 15,
    lineHeight: 22,
    borderWidth: 1,
  },
  charCount: {
    fontSize: 11,
    textAlign: "right",
    marginTop: 4,
    paddingHorizontal: 4,
  },

  // Layer
  layerSection: {
    marginBottom: 16,
  },
  layerRow: {
    flexDirection: "row",
    gap: 10,
  },
  layerOption: {
    flex: 1,
    paddingVertical: 14,
    paddingHorizontal: 12,
    borderRadius: 14,
    alignItems: "center",
    borderWidth: 1.5,
  },
  layerEmoji: {
    fontSize: 24,
    marginBottom: 4,
  },
  layerLabel: {
    fontSize: 14,
    fontWeight: "700",
    marginBottom: 2,
  },
  layerDesc: {
    fontSize: 11,
    textAlign: "center",
  },

  // GPS info
  gpsInfo: {
    borderRadius: 12,
    padding: 12,
    alignItems: "center",
    marginBottom: 8,
  },
  gpsText: {
    fontSize: 13,
    fontWeight: "500",
  },
  gpsHint: {
    fontSize: 11,
    marginTop: 2,
  },

  // Submit
  submitContainer: {
    paddingHorizontal: 20,
    paddingBottom: Platform.OS === "ios" ? 34 : 20,
    paddingTop: 8,
  },
  submitBtn: {
    paddingVertical: 16,
    borderRadius: 28,
    alignItems: "center",
    ...Platform.select({
      ios: {
        shadowColor: "#000",
        shadowOffset: { width: 0, height: 3 },
        shadowOpacity: 0.2,
        shadowRadius: 6,
      },
      android: { elevation: 6 },
    }),
  },
  submitText: {
    color: "#FFF",
    fontSize: 16,
    fontWeight: "800",
  },
});

export default memo(CreateArtifactSheetComponent);
