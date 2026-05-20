/**
 * LAYERS — SynchronicityModal Component
 * =====================================================
 * The magic moment. When the store's `pendingSync` is set (two strangers
 * unlocked the same artifact within 30 min), this full-screen modal fades
 * in with a quiet, mood-heavy message. No identities — just resonance.
 *
 * Mount this once near the app root (or in MapScreen). It self-shows when
 * pendingSync is non-null and clears it on dismiss.
 *
 * PATTERN: Animated fade, Colors[layer], no React.memo (single instance).
 */

import React, { useEffect, useRef } from "react";
import {
  Modal,
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Animated,
} from "react-native";
import { Colors } from "../../constants/colors";
import { useAuthStore } from "../../store/authStore";
import { useSocialSparkStore } from "../../store/socialSparkStore";
import { haptics } from "../../utils/haptics";

export default function SynchronicityModal() {
  const layer = useAuthStore((s) => s.layer);
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];

  const pendingSync = useSocialSparkStore((s) => s.pendingSync);
  const dismissSync = useSocialSparkStore((s) => s.dismissSync);

  const visible = pendingSync !== null;

  const fadeAnim = useRef(new Animated.Value(0)).current;
  const sparkleAnim = useRef(new Animated.Value(0.8)).current;

  useEffect(() => {
    if (visible) {
      haptics.success();
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 600,
        useNativeDriver: true,
      }).start();
      Animated.loop(
        Animated.sequence([
          Animated.timing(sparkleAnim, {
            toValue: 1.15,
            duration: 1200,
            useNativeDriver: true,
          }),
          Animated.timing(sparkleAnim, {
            toValue: 0.8,
            duration: 1200,
            useNativeDriver: true,
          }),
        ]),
      ).start();
    } else {
      fadeAnim.setValue(0);
    }
  }, [visible, fadeAnim, sparkleAnim]);

  if (!visible) return null;

  return (
    <Modal transparent visible={visible} animationType="none">
      <Animated.View
        style={[
          styles.backdrop,
          {
            opacity: fadeAnim,
            backgroundColor:
              layer === "SHADOW"
                ? "rgba(10, 8, 24, 0.94)"
                : "rgba(20, 20, 40, 0.92)",
          },
        ]}
      >
        <Animated.Text
          style={[styles.sparkle, { transform: [{ scale: sparkleAnim }] }]}
        >
          ✨
        </Animated.Text>

        <Text style={styles.title}>Synchronicity</Text>

        <Text style={styles.body}>
          Someone else unlocked this exact memory{"\n"}
          just moments apart from you.
        </Text>

        <Text style={styles.subtle}>
          You'll never know who. They'll never know you.{"\n"}
          But for one moment, this place held you both.
        </Text>

        <TouchableOpacity
          onPress={() => {
            haptics.light();
            dismissSync();
          }}
          style={[styles.button, { borderColor: "rgba(255,255,255,0.3)" }]}
          activeOpacity={0.7}
        >
          <Text style={styles.buttonText}>Hold this feeling</Text>
        </TouchableOpacity>
      </Animated.View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 40,
  },
  sparkle: {
    fontSize: 64,
    marginBottom: 20,
  },
  title: {
    color: "#FFFFFF",
    fontSize: 28,
    fontWeight: "700",
    letterSpacing: 1,
    marginBottom: 18,
  },
  body: {
    color: "#FFFFFF",
    fontSize: 17,
    lineHeight: 26,
    textAlign: "center",
    marginBottom: 20,
  },
  subtle: {
    color: "rgba(255,255,255,0.6)",
    fontSize: 14,
    lineHeight: 22,
    textAlign: "center",
    fontStyle: "italic",
    marginBottom: 40,
  },
  button: {
    paddingHorizontal: 28,
    paddingVertical: 14,
    borderRadius: 26,
    borderWidth: 1,
  },
  buttonText: {
    color: "#FFFFFF",
    fontSize: 15,
    fontWeight: "600",
  },
});
