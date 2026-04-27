/**
 * LAYERS — PaperPlaneScreen
 * ==========================================
 * Compose a short message (280 chars max), tap throw,
 * watch the animation, the plane lands 200m-1km away.
 *
 * FLOW:
 *   1. User taps "Paper Plane" from Map or Profile
 *   2. Screen opens with text input + throw button
 *   3. User types message (280 char limit)
 *   4. Tap "Throw ✈️" → API call
 *   5. ThrowAnimation plays (2s)
 *   6. Success alert → back to previous screen
 */

import React, { useState, useCallback, useMemo } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
  Alert,
  ScrollView,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useAuthStore } from "../../store/authStore";
import { useLocationStore } from "../../store/locationStore";
import { Colors } from "../../constants/colors";
import { paperPlaneService } from "../../services/planes_capsules";
import ThrowAnimation from "../../components/planes/ThrowAnimation";

const MAX_LENGTH = 280;

interface Props {
  onBack?: () => void;
}

export default function PaperPlaneScreen({ onBack }: Props) {
  const layer = useAuthStore((s) => s.layer);
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];
  const currentLocation = useLocationStore((s) => s.currentLocation);

  // State
  const [text, setText] = useState("");
  const [isThrowing, setIsThrowing] = useState(false);
  const [showAnimation, setShowAnimation] = useState(false);
  const [landingDistance, setLandingDistance] = useState(0);

  // Character count
  const remainingChars = MAX_LENGTH - text.length;
  const isOverLimit = remainingChars < 0;
  const canThrow = text.trim().length > 0 && !isOverLimit && !isThrowing;

  // Progress ring color
  const counterColor = useMemo(() => {
    if (isOverLimit) return "#EF4444";
    if (remainingChars < 30) return "#F59E0B";
    return colors.textSecondary;
  }, [isOverLimit, remainingChars, colors.textSecondary]);

  // ========================================================
  // THROW
  // ========================================================

  const handleThrow = useCallback(async () => {
    if (!canThrow) return;

    if (!currentLocation) {
      Alert.alert(
        "Location needed",
        "Turn on location to throw paper planes. They need to launch from somewhere real!",
        [{ text: "OK" }],
      );
      return;
    }

    setIsThrowing(true);

    try {
      const response = await paperPlaneService.throwPlane({
        text: text.trim(),
        latitude: currentLocation.latitude,
        longitude: currentLocation.longitude,
      });

      setLandingDistance(response.flight_distance_meters);
      setShowAnimation(true);
    } catch (error: any) {
      const message =
        error?.response?.data?.detail || "Failed to throw plane. Try again.";
      Alert.alert("Couldn't throw", message);
      setIsThrowing(false);
    }
  }, [canThrow, currentLocation, text]);

  const handleAnimationComplete = useCallback(() => {
    setShowAnimation(false);
    setIsThrowing(false);

    Alert.alert(
      "✈️ Plane launched!",
      `Your note flew ${Math.round(landingDistance)}m. Someone wandering nearby will find it soon.`,
      [
        {
          text: "Throw Another",
          onPress: () => setText(""),
        },
        {
          text: "Done",
          onPress: () => {
            setText("");
            onBack?.();
          },
        },
      ],
    );
  }, [landingDistance, onBack]);

  // ========================================================
  // RENDER
  // ========================================================

  return (
    <SafeAreaView
      style={[styles.container, { backgroundColor: colors.background }]}
      edges={["top"]}
    >
      {showAnimation && (
        <ThrowAnimation
          landingDistance={landingDistance}
          onComplete={handleAnimationComplete}
        />
      )}

      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        style={{ flex: 1 }}
      >
        {/* Header */}
        <View style={styles.header}>
          {onBack && (
            <TouchableOpacity onPress={onBack} disabled={isThrowing}>
              <Text style={[styles.backText, { color: colors.primary }]}>
                ← Back
              </Text>
            </TouchableOpacity>
          )}
          <Text style={[styles.headerTitle, { color: colors.text }]}>
            ✈️ Paper Plane
          </Text>
          <Text style={[styles.headerSub, { color: colors.textSecondary }]}>
            Write a note. Throw it. It lands 200m–1km away for a stranger.
          </Text>
        </View>

        <ScrollView
          contentContainerStyle={styles.scroll}
          keyboardShouldPersistTaps="handled"
        >
          {/* Text input card */}
          <View
            style={[
              styles.card,
              {
                backgroundColor: colors.surface,
                borderColor: isOverLimit ? "#EF4444" : colors.border,
              },
            ]}
          >
            <TextInput
              value={text}
              onChangeText={setText}
              multiline
              autoFocus
              placeholder={
                "Something for a stranger to find...\n\nA kind note. A secret. A joke.\nAnything you'd want to read."
              }
              placeholderTextColor={colors.textSecondary + "80"}
              style={[styles.input, { color: colors.text }]}
              maxLength={MAX_LENGTH + 20}
              editable={!isThrowing}
            />
            <View style={styles.cardFooter}>
              <Text style={[styles.counter, { color: counterColor }]}>
                {remainingChars}
              </Text>
            </View>
          </View>

          {/* Info box */}
          <View
            style={[
              styles.infoBox,
              { backgroundColor: colors.surface, borderColor: colors.border },
            ]}
          >
            <Text style={[styles.infoTitle, { color: colors.text }]}>
              How it works
            </Text>
            <View style={styles.infoRow}>
              <Text style={styles.infoIcon}>🎲</Text>
              <Text style={[styles.infoText, { color: colors.textSecondary }]}>
                Random landing spot between 200m and 1km away
              </Text>
            </View>
            <View style={styles.infoRow}>
              <Text style={styles.infoIcon}>👤</Text>
              <Text style={[styles.infoText, { color: colors.textSecondary }]}>
                Anonymous by default — no one sees your name
              </Text>
            </View>
            <View style={styles.infoRow}>
              <Text style={styles.infoIcon}>🗺️</Text>
              <Text style={[styles.infoText, { color: colors.textSecondary }]}>
                Shows as ✈️ on someone else's map
              </Text>
            </View>
            <View style={styles.infoRow}>
              <Text style={styles.infoIcon}>📍</Text>
              <Text style={[styles.infoText, { color: colors.textSecondary }]}>
                They must walk within 50m to read it
              </Text>
            </View>
          </View>
        </ScrollView>

        {/* Throw button */}
        <View style={styles.footer}>
          <TouchableOpacity
            onPress={handleThrow}
            disabled={!canThrow}
            style={[
              styles.throwButton,
              {
                backgroundColor: canThrow ? colors.primary : colors.border,
                opacity: canThrow ? 1 : 0.6,
              },
            ]}
            activeOpacity={0.85}
          >
            {isThrowing ? (
              <ActivityIndicator color="#FFFFFF" />
            ) : (
              <Text style={styles.throwButtonText}>Throw ✈️</Text>
            )}
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

// ============================================================
// STYLES
// ============================================================

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: {
    paddingHorizontal: 16,
    paddingTop: 8,
    paddingBottom: 12,
  },
  backText: { fontSize: 15, fontWeight: "500", marginBottom: 10 },
  headerTitle: {
    fontSize: 28,
    fontWeight: "bold",
    letterSpacing: -0.5,
    marginBottom: 4,
  },
  headerSub: { fontSize: 13, lineHeight: 18 },
  scroll: { padding: 16, gap: 14 },
  card: {
    borderWidth: 1,
    borderRadius: 14,
    padding: 14,
    minHeight: 200,
  },
  input: {
    fontSize: 16,
    lineHeight: 24,
    minHeight: 140,
    textAlignVertical: "top",
  },
  cardFooter: {
    flexDirection: "row",
    justifyContent: "flex-end",
    marginTop: 8,
  },
  counter: { fontSize: 13, fontWeight: "600" },
  infoBox: {
    borderWidth: 1,
    borderRadius: 14,
    padding: 14,
    gap: 10,
  },
  infoTitle: { fontSize: 14, fontWeight: "600", marginBottom: 4 },
  infoRow: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: 10,
  },
  infoIcon: { fontSize: 16, width: 24 },
  infoText: { fontSize: 13, flex: 1, lineHeight: 18 },
  footer: { padding: 16, paddingTop: 8 },
  throwButton: {
    paddingVertical: 16,
    borderRadius: 14,
    alignItems: "center",
  },
  throwButtonText: {
    color: "#FFFFFF",
    fontSize: 17,
    fontWeight: "700",
  },
});
