/**
 * LAYERS - Artifact Marker Component
 * ====================================
 * FILE: mobile/src/components/map/ArtifactMarker.tsx
 *
 * Renders a single artifact marker on the map.
 * Shows different emojis for Light vs Shadow mode.
 * Pulses when user is within 50m unlock range.
 * Locked appearance when out of range.
 *
 * USED IN: MapScreen.tsx (Week 2) — added as <Marker> children
 *
 * DESIGN:
 *   - Within range (< 50m): Glowing, pulsing, emoji visible → "Come get me!"
 *   - Out of range (> 50m): Dimmed, lock icon, smaller → "Walk closer!"
 *   - Already unlocked: Checkmark overlay → "You've been here"
 */

import React, { useEffect, useRef, memo } from "react";
import {
  View,
  Text,
  StyleSheet,
  Animated,
  TouchableOpacity,
  Platform,
} from "react-native";
import { Marker } from "react-native-maps";
import {
  ArtifactMarker as ArtifactMarkerType,
  MARKER_CONFIGS,
} from "../../types/artifact";
import { useAuthStore } from "../../store/authStore";

// ============================================================
// PROPS
// ============================================================

interface Props {
  artifact: ArtifactMarkerType;
  onPress: (artifact: ArtifactMarkerType) => void;
  isSelected?: boolean;
  isShadow?: boolean;
}

// ============================================================
// COMPONENT
// ============================================================

function ArtifactMarkerComponent({ artifact, onPress }: Props) {
  const { layer } = useAuthStore();
  const isShadow = layer === "SHADOW";
  const config = MARKER_CONFIGS[artifact.content_type];

  // Animation refs
  const pulseAnim = useRef(new Animated.Value(1)).current;
  const glowAnim = useRef(new Animated.Value(0.3)).current;
  const bounceAnim = useRef(new Animated.Value(0)).current;

  // Pulse animation when within range
  useEffect(() => {
    if (artifact.is_within_range && !artifact.is_unlocked) {
      // Exciting pulse — "You can open this!"
      const pulse = Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, {
            toValue: 1.2,
            duration: 800,
            useNativeDriver: true,
          }),
          Animated.timing(pulseAnim, {
            toValue: 1,
            duration: 800,
            useNativeDriver: true,
          }),
        ]),
      );

      const glow = Animated.loop(
        Animated.sequence([
          Animated.timing(glowAnim, {
            toValue: 0.8,
            duration: 1000,
            useNativeDriver: true,
          }),
          Animated.timing(glowAnim, {
            toValue: 0.3,
            duration: 1000,
            useNativeDriver: true,
          }),
        ]),
      );

      pulse.start();
      glow.start();
      return () => {
        pulse.stop();
        glow.stop();
      };
    }
  }, [artifact.is_within_range, artifact.is_unlocked]);

  // Bounce when first appears
  useEffect(() => {
    Animated.spring(bounceAnim, {
      toValue: 1,
      friction: 4,
      tension: 80,
      useNativeDriver: true,
    }).start();
  }, []);

  // Pick emoji based on layer mode
  const emoji = isShadow ? config.shadowEmoji : config.lightEmoji;
  const markerColor = isShadow ? config.shadowColor : config.color;
  const isLocked = !artifact.is_within_range;
  const isOpened = artifact.is_unlocked;

  return (
    <Marker
      coordinate={{
        latitude: artifact.latitude,
        longitude: artifact.longitude,
      }}
      anchor={{ x: 0.5, y: 0.5 }}
      tracksViewChanges={false} // Performance: don't re-render every frame
      onPress={() => onPress(artifact)}
    >
      <Animated.View
        style={[styles.container, { transform: [{ scale: bounceAnim }] }]}
      >
        {/* Glow ring (only when in range + not opened) */}
        {artifact.is_within_range && !isOpened && (
          <Animated.View
            style={[
              styles.glowRing,
              {
                backgroundColor: markerColor,
                opacity: glowAnim,
                transform: [{ scale: pulseAnim }],
              },
            ]}
          />
        )}

        {/* Main marker bubble */}
        <Animated.View
          style={[
            styles.markerBubble,
            {
              backgroundColor: isLocked
                ? isShadow
                  ? "rgba(30, 30, 40, 0.85)"
                  : "rgba(255, 255, 255, 0.85)"
                : markerColor + "DD",
              borderColor: isLocked
                ? isShadow
                  ? "rgba(100, 100, 120, 0.5)"
                  : "rgba(200, 200, 200, 0.5)"
                : markerColor,
              transform: [{ scale: artifact.is_within_range ? pulseAnim : 1 }],
            },
          ]}
        >
          {/* Emoji */}
          <Text style={[styles.emoji, isLocked && styles.emojiLocked]}>
            {isLocked ? "🔒" : emoji}
          </Text>

          {/* Opened checkmark */}
          {isOpened && (
            <View style={styles.checkBadge}>
              <Text style={styles.checkText}>✓</Text>
            </View>
          )}

          {/* Reply count badge */}
          {artifact.preview.reply_count > 0 && !isLocked && (
            <View style={[styles.replyBadge, { backgroundColor: markerColor }]}>
              <Text style={styles.replyText}>
                {artifact.preview.reply_count > 9
                  ? "9+"
                  : artifact.preview.reply_count}
              </Text>
            </View>
          )}
        </Animated.View>

        {/* Distance label */}
        {isLocked && (
          <View
            style={[
              styles.distanceLabel,
              {
                backgroundColor: isShadow
                  ? "rgba(30, 30, 40, 0.9)"
                  : "rgba(255, 255, 255, 0.9)",
              },
            ]}
          >
            <Text
              style={[
                styles.distanceText,
                {
                  color: isShadow ? "#A78BFA" : "#6B7280",
                },
              ]}
            >
              {formatDistance(artifact.distance_meters)}
            </Text>
          </View>
        )}

        {/* Type label when in range */}
        {!isLocked && !isOpened && (
          <View
            style={[styles.typeLabel, { backgroundColor: markerColor + "CC" }]}
          >
            <Text style={styles.typeLabelText}>{config.label}</Text>
          </View>
        )}
      </Animated.View>
    </Marker>
  );
}

// ============================================================
// HELPERS
// ============================================================

function formatDistance(meters: number): string {
  if (meters < 100) return `${Math.round(meters)}m`;
  if (meters < 1000) return `${Math.round(meters / 10) * 10}m`;
  return `${(meters / 1000).toFixed(1)}km`;
}

// ============================================================
// STYLES
// ============================================================

const styles = StyleSheet.create({
  container: {
    alignItems: "center",
    justifyContent: "center",
    width: 60,
    height: 70,
  },
  glowRing: {
    position: "absolute",
    width: 52,
    height: 52,
    borderRadius: 26,
    top: 2,
  },
  markerBubble: {
    width: 44,
    height: 44,
    borderRadius: 22,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 2,
    // Shadow for depth
    ...Platform.select({
      ios: {
        shadowColor: "#000",
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.25,
        shadowRadius: 4,
      },
      android: {
        elevation: 4,
      },
    }),
  },
  emoji: {
    fontSize: 22,
  },
  emojiLocked: {
    fontSize: 16,
    opacity: 0.7,
  },
  checkBadge: {
    position: "absolute",
    top: -2,
    right: -2,
    width: 16,
    height: 16,
    borderRadius: 8,
    backgroundColor: "#10B981",
    alignItems: "center",
    justifyContent: "center",
  },
  checkText: {
    color: "#FFF",
    fontSize: 10,
    fontWeight: "bold",
  },
  replyBadge: {
    position: "absolute",
    top: -4,
    right: -6,
    minWidth: 18,
    height: 18,
    borderRadius: 9,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 4,
    borderWidth: 1.5,
    borderColor: "#FFF",
  },
  replyText: {
    color: "#FFF",
    fontSize: 9,
    fontWeight: "bold",
  },
  distanceLabel: {
    marginTop: 2,
    paddingHorizontal: 6,
    paddingVertical: 1,
    borderRadius: 8,
  },
  distanceText: {
    fontSize: 9,
    fontWeight: "600",
  },
  typeLabel: {
    marginTop: 2,
    paddingHorizontal: 6,
    paddingVertical: 1,
    borderRadius: 8,
  },
  typeLabelText: {
    color: "#FFF",
    fontSize: 9,
    fontWeight: "600",
  },
});

// Memoize to avoid re-renders when other markers change
export default memo(ArtifactMarkerComponent);
