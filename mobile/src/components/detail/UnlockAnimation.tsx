/**
 * LAYERS - Unlock Animation
 * ====================================
 * The DOPAMINE MOMENT — user walks to an artifact, taps unlock,
 * and the content is revealed with a gorgeous animation.
 *
 * SEQUENCE (1.2s total):
 *   1. Lock icon shatters outward (200ms)
 *   2. Bright flash from center (100ms)
 *   3. Content container scales in with spring (500ms)
 *   4. Sparkle particles scatter (600ms)
 *   5. Subtle haptic pattern: tap-tap-THUD
 *
 * Used inside ArtifactDetailSheet when transitioning
 * from locked → unlocked state.
 */

import React, { useEffect, useRef, memo } from "react";
import {
  View,
  Text,
  StyleSheet,
  Animated,
  Easing,
  Platform,
} from "react-native";
import * as Haptics from "expo-haptics";

interface Props {
  /** Triggers the animation when true */
  isUnlocking: boolean;
  /** Called when animation finishes */
  onComplete: () => void;
  isShadow: boolean;
}

const SHARD_COUNT = 6;
const SPARKLE_COUNT = 8;

function UnlockAnimationComponent({
  isUnlocking,
  onComplete,
  isShadow,
}: Props) {
  // Lock icon
  const lockScale = useRef(new Animated.Value(1)).current;
  const lockOpacity = useRef(new Animated.Value(1)).current;

  // Flash
  const flashOpacity = useRef(new Animated.Value(0)).current;
  const flashScale = useRef(new Animated.Value(0.5)).current;

  // Content reveal
  const contentScale = useRef(new Animated.Value(0.3)).current;
  const contentOpacity = useRef(new Animated.Value(0)).current;

  // Lock shards (pieces flying outward)
  const shards = useRef(
    Array.from({ length: SHARD_COUNT }, () => ({
      translateX: new Animated.Value(0),
      translateY: new Animated.Value(0),
      rotate: new Animated.Value(0),
      opacity: new Animated.Value(0),
      scale: new Animated.Value(1),
    })),
  ).current;

  // Sparkles
  const sparkles = useRef(
    Array.from({ length: SPARKLE_COUNT }, () => ({
      translateX: new Animated.Value(0),
      translateY: new Animated.Value(0),
      opacity: new Animated.Value(0),
      scale: new Animated.Value(0),
    })),
  ).current;

  useEffect(() => {
    if (!isUnlocking) return;

    // Reset
    lockScale.setValue(1);
    lockOpacity.setValue(1);
    flashOpacity.setValue(0);
    flashScale.setValue(0.5);
    contentScale.setValue(0.3);
    contentOpacity.setValue(0);

    // Haptic sequence: light-light-MEDIUM
    const hapticSequence = async () => {
      if (Platform.OS === "web") return;
      await Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
      setTimeout(
        () => Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light),
        100,
      );
      setTimeout(
        () => Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy),
        250,
      );
    };
    hapticSequence();

    // Phase 1: Lock shakes then shatters
    const lockShake = Animated.sequence([
      Animated.timing(lockScale, {
        toValue: 1.15,
        duration: 100,
        useNativeDriver: true,
      }),
      Animated.timing(lockScale, {
        toValue: 0.9,
        duration: 60,
        useNativeDriver: true,
      }),
      Animated.timing(lockScale, {
        toValue: 1.2,
        duration: 80,
        useNativeDriver: true,
      }),
    ]);

    const lockShatter = Animated.parallel([
      Animated.timing(lockScale, {
        toValue: 0,
        duration: 150,
        useNativeDriver: true,
      }),
      Animated.timing(lockOpacity, {
        toValue: 0,
        duration: 150,
        useNativeDriver: true,
      }),
    ]);

    // Phase 1b: Shards fly out
    const shardAnims = shards.map((s, i) => {
      const angle = (i / SHARD_COUNT) * Math.PI * 2;
      const dist = 40 + Math.random() * 30;
      s.opacity.setValue(1);
      return Animated.parallel([
        Animated.timing(s.translateX, {
          toValue: Math.cos(angle) * dist,
          duration: 400,
          easing: Easing.out(Easing.cubic),
          useNativeDriver: true,
        }),
        Animated.timing(s.translateY, {
          toValue: Math.sin(angle) * dist,
          duration: 400,
          easing: Easing.out(Easing.cubic),
          useNativeDriver: true,
        }),
        Animated.timing(s.rotate, {
          toValue: Math.random() * 4 - 2,
          duration: 400,
          useNativeDriver: true,
        }),
        Animated.timing(s.opacity, {
          toValue: 0,
          duration: 400,
          delay: 100,
          useNativeDriver: true,
        }),
      ]);
    });

    // Phase 2: Flash
    const flash = Animated.parallel([
      Animated.timing(flashOpacity, {
        toValue: 0.8,
        duration: 80,
        useNativeDriver: true,
      }),
      Animated.timing(flashScale, {
        toValue: 2.5,
        duration: 300,
        easing: Easing.out(Easing.cubic),
        useNativeDriver: true,
      }),
      Animated.timing(flashOpacity, {
        toValue: 0,
        duration: 300,
        delay: 80,
        useNativeDriver: true,
      }),
    ]);

    // Phase 3: Content reveal
    const reveal = Animated.parallel([
      Animated.spring(contentScale, {
        toValue: 1,
        friction: 5,
        tension: 100,
        useNativeDriver: true,
      }),
      Animated.timing(contentOpacity, {
        toValue: 1,
        duration: 300,
        useNativeDriver: true,
      }),
    ]);

    // Phase 4: Sparkles
    const sparkleAnims = sparkles.map((s, i) => {
      const angle = (i / SPARKLE_COUNT) * Math.PI * 2 + Math.random() * 0.5;
      const dist = 30 + Math.random() * 50;
      return Animated.parallel([
        Animated.timing(s.translateX, {
          toValue: Math.cos(angle) * dist,
          duration: 500,
          easing: Easing.out(Easing.cubic),
          useNativeDriver: true,
        }),
        Animated.timing(s.translateY, {
          toValue: Math.sin(angle) * dist,
          duration: 500,
          easing: Easing.out(Easing.cubic),
          useNativeDriver: true,
        }),
        Animated.sequence([
          Animated.timing(s.opacity, {
            toValue: 1,
            duration: 100,
            useNativeDriver: true,
          }),
          Animated.timing(s.scale, {
            toValue: 1.3,
            duration: 150,
            useNativeDriver: true,
          }),
          Animated.timing(s.opacity, {
            toValue: 0,
            duration: 250,
            useNativeDriver: true,
          }),
        ]),
      ]);
    });

    // Run all
    Animated.sequence([
      lockShake,
      Animated.parallel([lockShatter, ...shardAnims, flash]),
      Animated.parallel([reveal, ...sparkleAnims]),
    ]).start(() => {
      onComplete();
    });
  }, [isUnlocking]);

  if (!isUnlocking) return null;

  const accent = isShadow ? "#8B5CF6" : "#3B82F6";

  return (
    <View style={styles.container} pointerEvents="none">
      {/* Lock icon that shatters */}
      <Animated.Text
        style={[
          styles.lockIcon,
          { opacity: lockOpacity, transform: [{ scale: lockScale }] },
        ]}
      >
        🔒
      </Animated.Text>

      {/* Shards */}
      {shards.map((s, i) => (
        <Animated.Text
          key={`shard-${i}`}
          style={[
            styles.shard,
            {
              opacity: s.opacity,
              transform: [
                { translateX: s.translateX },
                { translateY: s.translateY },
                {
                  rotate: s.rotate.interpolate({
                    inputRange: [-2, 2],
                    outputRange: ["-180deg", "180deg"],
                  }),
                },
                { scale: s.scale },
              ],
            },
          ]}
        >
          {["🔓", "✦", "⚡", "💫", "✧", "🗝️"][i % 6]}
        </Animated.Text>
      ))}

      {/* Flash */}
      <Animated.View
        style={[
          styles.flash,
          {
            backgroundColor: accent,
            opacity: flashOpacity,
            transform: [{ scale: flashScale }],
          },
        ]}
      />

      {/* Sparkles */}
      {sparkles.map((s, i) => (
        <Animated.Text
          key={`sparkle-${i}`}
          style={[
            styles.sparkle,
            {
              opacity: s.opacity,
              transform: [
                { translateX: s.translateX },
                { translateY: s.translateY },
                { scale: s.scale },
              ],
            },
          ]}
        >
          ✨
        </Animated.Text>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: "center",
    justifyContent: "center",
    height: 80,
    marginVertical: 8,
  },
  lockIcon: { fontSize: 40, position: "absolute" },
  shard: { position: "absolute", fontSize: 16 },
  flash: { position: "absolute", width: 30, height: 30, borderRadius: 15 },
  sparkle: { position: "absolute", fontSize: 14 },
});

export default memo(UnlockAnimationComponent);
