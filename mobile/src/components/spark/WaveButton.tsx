/**
 * LAYERS — WaveButton Component
 * ==============================================
 * A floating "wave 👋" button for MapScreen. One tap drops an anonymous
 * wave at the user's location. Shows an animated confirmation + how many
 * others waved nearby.
 *
 * PATTERN: React.memo, Colors[layer], Animated pulse on success.
 */

import React, { useEffect, useRef, useCallback, useState } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Animated,
  ActivityIndicator,
} from "react-native";
import { Colors } from "../../constants/colors";
import { useAuthStore } from "../../store/authStore";
import { useSocialSparkStore } from "../../store/socialSparkStore";
import { haptics } from "../../utils/haptics";

interface WaveButtonProps {
  latitude: number | null;
  longitude: number | null;
}

function WaveButtonComponent({ latitude, longitude }: WaveButtonProps) {
  const layer = useAuthStore((s) => s.layer);
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];

  const isWaving = useSocialSparkStore((s) => s.isWaving);
  const wavesNearbyCount = useSocialSparkStore((s) => s.wavesNearbyCount);
  const lastWaveResult = useSocialSparkStore((s) => s.lastWaveResult);
  const waveError = useSocialSparkStore((s) => s.error);
  const wave = useSocialSparkStore((s) => s.wave);
  const fetchWavesNearby = useSocialSparkStore((s) => s.fetchWavesNearby);

  const scaleAnim = useRef(new Animated.Value(1)).current;
  const toastOpacity = useRef(new Animated.Value(0)).current;
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const toastTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const showToast = useCallback(
    (msg: string) => {
      if (toastTimer.current) clearTimeout(toastTimer.current);
      setToastMessage(msg);
      toastOpacity.setValue(0);
      Animated.timing(toastOpacity, {
        toValue: 1,
        duration: 200,
        useNativeDriver: true,
      }).start();
      toastTimer.current = setTimeout(() => {
        Animated.timing(toastOpacity, {
          toValue: 0,
          duration: 350,
          useNativeDriver: true,
        }).start(() => setToastMessage(null));
      }, 3000);
    },
    [toastOpacity],
  );

  // Show toast on success or rate-limit error
  useEffect(() => {
    if (lastWaveResult) {
      showToast(
        lastWaveResult.wavedBack
          ? `👋 ${lastWaveResult.others} waved back near you!`
          : "👋 Wave sent — the city heard you",
      );
    }
  }, [lastWaveResult]);

  useEffect(() => {
    if (waveError) showToast(waveError);
  }, [waveError]);

  // Poll nearby wave count occasionally
  useEffect(() => {
    if (latitude == null || longitude == null) return;
    fetchWavesNearby(latitude, longitude);
    const interval = setInterval(() => {
      fetchWavesNearby(latitude, longitude);
    }, 30_000);
    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [latitude, longitude]);

  const handlePress = useCallback(async () => {
    if (latitude == null || longitude == null) return;
    haptics.light();
    await wave(latitude, longitude);
    Animated.sequence([
      Animated.timing(scaleAnim, {
        toValue: 1.3,
        duration: 150,
        useNativeDriver: true,
      }),
      Animated.timing(scaleAnim, {
        toValue: 1,
        duration: 250,
        useNativeDriver: true,
      }),
    ]).start();
  }, [latitude, longitude, wave, scaleAnim]);

  const disabled = isWaving || latitude == null || longitude == null;

  return (
    <View style={styles.wrap}>
      {/* Confirmation / error toast — absolutely positioned, auto-dismisses after 3s */}
      {toastMessage && (
        <Animated.View
          style={[
            styles.toast,
            { backgroundColor: colors.surface, opacity: toastOpacity },
          ]}
        >
          <Text style={[styles.toastText, { color: colors.text }]}>
            {toastMessage}
          </Text>
        </Animated.View>
      )}

      <Animated.View style={{ transform: [{ scale: scaleAnim }] }}>
        <TouchableOpacity
          onPress={handlePress}
          disabled={disabled}
          activeOpacity={0.8}
          style={[
            styles.button,
            { backgroundColor: colors.surface, opacity: disabled ? 0.6 : 1 },
          ]}
        >
          {isWaving ? (
            <ActivityIndicator size="small" color={colors.primary} />
          ) : (
            <Text style={styles.icon}>👋</Text>
          )}
          {wavesNearbyCount > 0 && (
            <View style={[styles.badge, { backgroundColor: colors.primary }]}>
              <Text style={styles.badgeText}>{wavesNearbyCount}</Text>
            </View>
          )}
        </TouchableOpacity>
      </Animated.View>
    </View>
  );
}

export const WaveButton = React.memo(WaveButtonComponent);
WaveButton.displayName = "WaveButton";

const styles = StyleSheet.create({
  wrap: {
    width: 52,
    height: 52,
    alignItems: "center",
    justifyContent: "center",
  },
  toast: {
    position: "absolute",
    right: 62,
    top: 4,
    width: 190,
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 14,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.15,
    shadowRadius: 6,
    elevation: 4,
  },
  toastText: {
    fontSize: 13,
    fontWeight: "500",
  },
  button: {
    width: 52,
    height: 52,
    borderRadius: 26,
    alignItems: "center",
    justifyContent: "center",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 6,
    elevation: 5,
  },
  icon: {
    fontSize: 24,
  },
  badge: {
    position: "absolute",
    top: -2,
    right: -2,
    minWidth: 20,
    height: 20,
    borderRadius: 10,
    paddingHorizontal: 5,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 2,
    borderColor: "#FFFFFF",
  },
  badgeText: {
    color: "#FFFFFF",
    fontSize: 11,
    fontWeight: "700",
  },
});

export default WaveButton;
