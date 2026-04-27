/**
 * LAYERS — CapsuleCard Component
 * ==========================================
 * Displays a time capsule with live countdown.
 *
 * States:
 *   LOCKED:   Sealed wax effect, countdown timer, can't read
 *   UNLOCKED: Glow effect, "Tap to open" message
 */

import React, { useEffect, useState, useCallback, useMemo } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Animated,
} from "react-native";
import { Colors } from "../../constants/colors";
import { useAuthStore } from "../../store/authStore";
import {
  calculateCountdown,
  CapsuleCountdown,
} from "../../types/planes_capsules";

// ============================================================
// TYPES
// ============================================================

export interface CapsuleItem {
  id: string;
  payload: { text?: string };
  unlock_at: string | null;
  created_at: string;
  latitude: number;
  longitude: number;
}

interface CapsuleCardProps {
  capsule: CapsuleItem;
  onPress?: (capsule: CapsuleItem) => void;
}

// ============================================================
// COMPONENT
// ============================================================

const CapsuleCard = React.memo(({ capsule, onPress }: CapsuleCardProps) => {
  const layer = useAuthStore((s) => s.layer);
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];

  // Live countdown state
  const [countdown, setCountdown] = useState<CapsuleCountdown>(() =>
    capsule.unlock_at
      ? calculateCountdown(capsule.unlock_at)
      : {
          days: 0,
          hours: 0,
          minutes: 0,
          seconds: 0,
          is_unlocked: true,
          formatted: "No unlock date",
        },
  );

  // Update countdown every second (for unlocked items, stop)
  useEffect(() => {
    if (!capsule.unlock_at || countdown.is_unlocked) return;

    const interval = setInterval(() => {
      setCountdown(calculateCountdown(capsule.unlock_at!));
    }, 1000);

    return () => clearInterval(interval);
  }, [capsule.unlock_at, countdown.is_unlocked]);

  // Pulse animation when unlocked
  const pulseAnim = React.useRef(new Animated.Value(1)).current;
  useEffect(() => {
    if (countdown.is_unlocked) {
      Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, {
            toValue: 1.05,
            duration: 1200,
            useNativeDriver: true,
          }),
          Animated.timing(pulseAnim, {
            toValue: 1,
            duration: 1200,
            useNativeDriver: true,
          }),
        ]),
      ).start();
    }
  }, [countdown.is_unlocked]);

  const unlockDate = useMemo(() => {
    if (!capsule.unlock_at) return "—";
    return new Date(capsule.unlock_at).toLocaleDateString("en-US", {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  }, [capsule.unlock_at]);

  const createdDate = useMemo(() => {
    return new Date(capsule.created_at).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }, [capsule.created_at]);

  const handlePress = useCallback(() => {
    onPress?.(capsule);
  }, [capsule, onPress]);

  const isLocked = !countdown.is_unlocked;

  return (
    <Animated.View style={{ transform: [{ scale: pulseAnim }] }}>
      <TouchableOpacity
        onPress={handlePress}
        activeOpacity={0.85}
        style={[
          styles.card,
          {
            backgroundColor: colors.surface,
            borderColor: isLocked ? colors.border : colors.primary + "80",
            borderLeftColor: isLocked ? "#F59E0B" : "#10B981",
            borderLeftWidth: 3,
          },
        ]}
      >
        {/* Header row */}
        <View style={styles.headerRow}>
          <View style={styles.iconContainer}>
            <Text style={styles.icon}>{isLocked ? "⏰" : "✨"}</Text>
            {isLocked && (
              <View style={styles.sealBadge}>
                <Text style={styles.sealIcon}>🔒</Text>
              </View>
            )}
          </View>

          <View style={styles.titleContainer}>
            <Text style={[styles.title, { color: colors.text }]}>
              {isLocked ? "Sealed Time Capsule" : "Ready to Open!"}
            </Text>
            <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
              Sealed on {createdDate}
            </Text>
          </View>
        </View>

        {/* Countdown section */}
        {isLocked ? (
          <View
            style={[
              styles.countdownBox,
              { backgroundColor: colors.background },
            ]}
          >
            <Text
              style={[styles.countdownLabel, { color: colors.textSecondary }]}
            >
              Opens in
            </Text>
            <Text style={[styles.countdownValue, { color: "#F59E0B" }]}>
              {countdown.formatted}
            </Text>

            {/* Granular time units for < 30 days */}
            {countdown.days < 30 && (
              <View style={styles.timeUnits}>
                <TimeUnit value={countdown.days} label="days" colors={colors} />
                <TimeUnit value={countdown.hours} label="hrs" colors={colors} />
                <TimeUnit
                  value={countdown.minutes}
                  label="min"
                  colors={colors}
                />
                <TimeUnit
                  value={countdown.seconds}
                  label="sec"
                  colors={colors}
                />
              </View>
            )}

            <Text style={[styles.unlockDate, { color: colors.textSecondary }]}>
              📅 {unlockDate}
            </Text>
          </View>
        ) : (
          <View style={[styles.unlockedBox, { backgroundColor: "#10B98115" }]}>
            <Text style={[styles.unlockedText, { color: "#10B981" }]}>
              🎉 Your capsule is ready to read
            </Text>
            <Text style={[styles.unlockedSub, { color: colors.textSecondary }]}>
              Tap to open
            </Text>
          </View>
        )}
      </TouchableOpacity>
    </Animated.View>
  );
});

CapsuleCard.displayName = "CapsuleCard";

// ============================================================
// TIME UNIT SUB-COMPONENT
// ============================================================

interface TimeUnitProps {
  value: number;
  label: string;
  colors: any;
}

function TimeUnit({ value, label, colors }: TimeUnitProps) {
  return (
    <View style={styles.unit}>
      <Text style={[styles.unitValue, { color: colors.text }]}>
        {value.toString().padStart(2, "0")}
      </Text>
      <Text style={[styles.unitLabel, { color: colors.textSecondary }]}>
        {label}
      </Text>
    </View>
  );
}

// ============================================================
// STYLES
// ============================================================

const styles = StyleSheet.create({
  card: {
    borderWidth: 1,
    borderRadius: 14,
    padding: 14,
    marginHorizontal: 16,
    marginBottom: 12,
  },
  headerRow: {
    flexDirection: "row",
    gap: 12,
    marginBottom: 12,
  },
  iconContainer: {
    position: "relative",
    width: 48,
    height: 48,
    alignItems: "center",
    justifyContent: "center",
  },
  icon: { fontSize: 36 },
  sealBadge: {
    position: "absolute",
    bottom: 0,
    right: 0,
    width: 18,
    height: 18,
    borderRadius: 9,
    backgroundColor: "#000",
    alignItems: "center",
    justifyContent: "center",
  },
  sealIcon: { fontSize: 10 },
  titleContainer: {
    flex: 1,
    justifyContent: "center",
  },
  title: { fontSize: 15, fontWeight: "600", marginBottom: 2 },
  subtitle: { fontSize: 12 },
  countdownBox: {
    padding: 14,
    borderRadius: 10,
    alignItems: "center",
  },
  countdownLabel: {
    fontSize: 11,
    textTransform: "uppercase",
    letterSpacing: 0.5,
    marginBottom: 4,
  },
  countdownValue: {
    fontSize: 22,
    fontWeight: "700",
    marginBottom: 10,
  },
  timeUnits: {
    flexDirection: "row",
    gap: 16,
    marginBottom: 10,
  },
  unit: { alignItems: "center" },
  unitValue: {
    fontSize: 18,
    fontWeight: "700",
    fontVariant: ["tabular-nums"],
  },
  unitLabel: {
    fontSize: 10,
    textTransform: "uppercase",
    letterSpacing: 0.5,
    marginTop: 2,
  },
  unlockDate: { fontSize: 12 },
  unlockedBox: {
    padding: 14,
    borderRadius: 10,
    alignItems: "center",
  },
  unlockedText: { fontSize: 14, fontWeight: "600", marginBottom: 2 },
  unlockedSub: { fontSize: 12 },
});

export default CapsuleCard;
