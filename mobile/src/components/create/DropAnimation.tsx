/**
 * LAYERS - Drop Animation
 * ====================================
 * The SATISFYING moment when user drops a memory on the map.
 * This is the "publish" dopamine hit.
 *
 * SEQUENCE:
 *   1. Artifact emoji appears at screen center, large
 *   2. Brief glow/scale-up pulse
 *   3. Floats downward toward the map (gravity feel)
 *   4. Sparkle particles burst outward at landing
 *   5. Subtle bounce at final position
 *   6. Fades out → new marker visible on map
 *
 * Duration: ~1.2 seconds total
 * Triggers: After POST /artifacts returns success
 */

import React, { useEffect, useRef, memo } from "react";
import {
  View,
  Text,
  StyleSheet,
  Animated,
  Easing,
  Dimensions,
  Platform,
} from "react-native";
import * as Haptics from "expo-haptics";

const { height: SCREEN_HEIGHT } = Dimensions.get("window");

// ============================================================
// TYPES
// ============================================================

interface Props {
  /** Emoji to show for the dropped artifact */
  emoji: string;
  /** Whether to show the animation */
  visible: boolean;
  /** Called when animation completes */
  onComplete: () => void;
  /** Shadow mode styling */
  isShadow: boolean;
}

// ============================================================
// SPARKLE PARTICLES
// ============================================================

const SPARKLE_COUNT = 10;
const SPARKLE_EMOJIS = ["✨", "⭐", "💫", "🌟", "✦"];

function getRandomSparkle() {
  return SPARKLE_EMOJIS[Math.floor(Math.random() * SPARKLE_EMOJIS.length)];
}

// ============================================================
// COMPONENT
// ============================================================

function DropAnimationComponent({
  emoji,
  visible,
  onComplete,
  isShadow,
}: Props) {
  // Main artifact animation
  const translateY = useRef(new Animated.Value(-50)).current;
  const scale = useRef(new Animated.Value(0.3)).current;
  const opacity = useRef(new Animated.Value(0)).current;
  const rotation = useRef(new Animated.Value(0)).current;

  // Landing flash
  const flashScale = useRef(new Animated.Value(0)).current;
  const flashOpacity = useRef(new Animated.Value(0)).current;

  // Sparkle particles
  const sparkles = useRef(
    Array.from({ length: SPARKLE_COUNT }, () => ({
      translateX: new Animated.Value(0),
      translateY: new Animated.Value(0),
      opacity: new Animated.Value(0),
      scale: new Animated.Value(0),
    })),
  ).current;

  // Success text
  const textOpacity = useRef(new Animated.Value(0)).current;
  const textTranslateY = useRef(new Animated.Value(10)).current;

  useEffect(() => {
    if (!visible) return;

    // Reset values
    translateY.setValue(-50);
    scale.setValue(0.3);
    opacity.setValue(0);
    rotation.setValue(0);
    flashScale.setValue(0);
    flashOpacity.setValue(0);
    textOpacity.setValue(0);
    textTranslateY.setValue(10);
    sparkles.forEach((s) => {
      s.translateX.setValue(0);
      s.translateY.setValue(0);
      s.opacity.setValue(0);
      s.scale.setValue(0);
    });

    // Phase 1: Appear + float up slightly (0-200ms)
    const appear = Animated.parallel([
      Animated.timing(opacity, {
        toValue: 1,
        duration: 150,
        useNativeDriver: true,
      }),
      Animated.timing(scale, {
        toValue: 1.3,
        duration: 200,
        easing: Easing.out(Easing.back(2)),
        useNativeDriver: true,
      }),
      Animated.timing(translateY, {
        toValue: -80,
        duration: 200,
        easing: Easing.out(Easing.quad),
        useNativeDriver: true,
      }),
    ]);

    // Phase 2: Drop down with gravity + slight rotation (200-700ms)
    const drop = Animated.parallel([
      Animated.timing(translateY, {
        toValue: 40,
        duration: 500,
        easing: Easing.in(Easing.quad), // Gravity acceleration
        useNativeDriver: true,
      }),
      Animated.timing(scale, {
        toValue: 0.9,
        duration: 500,
        useNativeDriver: true,
      }),
      Animated.timing(rotation, {
        toValue: 1,
        duration: 500,
        useNativeDriver: true,
      }),
    ]);

    // Phase 3: Bounce at landing (700-900ms)
    const bounce = Animated.parallel([
      Animated.spring(translateY, {
        toValue: 20,
        friction: 4,
        tension: 200,
        useNativeDriver: true,
      }),
      Animated.spring(scale, {
        toValue: 1,
        friction: 3,
        tension: 180,
        useNativeDriver: true,
      }),
    ]);

    // Phase 3b: Landing flash
    const flash = Animated.parallel([
      Animated.timing(flashOpacity, {
        toValue: 0.6,
        duration: 100,
        useNativeDriver: true,
      }),
      Animated.timing(flashScale, {
        toValue: 3,
        duration: 400,
        easing: Easing.out(Easing.cubic),
        useNativeDriver: true,
      }),
      Animated.timing(flashOpacity, {
        toValue: 0,
        duration: 400,
        delay: 100,
        useNativeDriver: true,
      }),
    ]);

    // Phase 3c: Sparkle burst
    const sparkleAnims = sparkles.map((s, i) => {
      const angle = (i / SPARKLE_COUNT) * Math.PI * 2;
      const distance = 50 + Math.random() * 40;
      return Animated.parallel([
        Animated.timing(s.translateX, {
          toValue: Math.cos(angle) * distance,
          duration: 600,
          easing: Easing.out(Easing.cubic),
          useNativeDriver: true,
        }),
        Animated.timing(s.translateY, {
          toValue: Math.sin(angle) * distance - 20, // Upward bias
          duration: 600,
          easing: Easing.out(Easing.cubic),
          useNativeDriver: true,
        }),
        Animated.sequence([
          Animated.timing(s.opacity, {
            toValue: 1,
            duration: 100,
            useNativeDriver: true,
          }),
          Animated.timing(s.opacity, {
            toValue: 0,
            duration: 500,
            useNativeDriver: true,
          }),
        ]),
        Animated.sequence([
          Animated.timing(s.scale, {
            toValue: 1.2,
            duration: 200,
            useNativeDriver: true,
          }),
          Animated.timing(s.scale, {
            toValue: 0,
            duration: 400,
            useNativeDriver: true,
          }),
        ]),
      ]);
    });

    // Phase 4: Success text slides up
    const successText = Animated.parallel([
      Animated.timing(textOpacity, {
        toValue: 1,
        duration: 300,
        useNativeDriver: true,
      }),
      Animated.timing(textTranslateY, {
        toValue: 0,
        duration: 300,
        easing: Easing.out(Easing.back(1.5)),
        useNativeDriver: true,
      }),
    ]);

    // Phase 5: Fade out everything
    const fadeOut = Animated.parallel([
      Animated.timing(opacity, {
        toValue: 0,
        duration: 400,
        delay: 300,
        useNativeDriver: true,
      }),
      Animated.timing(textOpacity, {
        toValue: 0,
        duration: 300,
        delay: 400,
        useNativeDriver: true,
      }),
    ]);

    // Haptics on land
    const triggerHaptic = () => {
      if (Platform.OS !== "web") {
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      }
    };

    // RUN SEQUENCE
    Animated.sequence([
      appear,
      drop,
      Animated.parallel([bounce, flash, ...sparkleAnims]),
    ]).start(() => {
      triggerHaptic();
      successText.start(() => {
        fadeOut.start(() => {
          onComplete();
        });
      });
    });
  }, [visible]);

  if (!visible) return null;

  const accentColor = isShadow ? "#8B5CF6" : "#3B82F6";
  const rotateInterpolate = rotation.interpolate({
    inputRange: [0, 1],
    outputRange: ["0deg", "8deg"],
  });

  return (
    <View style={styles.overlay} pointerEvents="none">
      {/* Landing flash circle */}
      <Animated.View
        style={[
          styles.flash,
          {
            backgroundColor: accentColor,
            opacity: flashOpacity,
            transform: [{ scale: flashScale }],
          },
        ]}
      />

      {/* Main artifact emoji */}
      <Animated.View
        style={[
          styles.emojiContainer,
          {
            opacity,
            transform: [
              { translateY },
              { scale },
              { rotate: rotateInterpolate },
            ],
          },
        ]}
      >
        <Text style={styles.emoji}>{emoji}</Text>
      </Animated.View>

      {/* Sparkle particles */}
      {sparkles.map((s, i) => (
        <Animated.Text
          key={i}
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
          {getRandomSparkle()}
        </Animated.Text>
      ))}

      {/* Success text */}
      <Animated.View
        style={[
          styles.successContainer,
          {
            opacity: textOpacity,
            transform: [{ translateY: textTranslateY }],
          },
        ]}
      >
        <Text style={[styles.successText, { color: accentColor }]}>
          {isShadow ? "Shadow dropped 🌙" : "Memory dropped ✨"}
        </Text>
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  overlay: {
    ...StyleSheet.absoluteFillObject,
    alignItems: "center",
    justifyContent: "center",
    zIndex: 1000,
  },
  emojiContainer: {
    alignItems: "center",
    justifyContent: "center",
  },
  emoji: {
    fontSize: 64,
  },
  flash: {
    position: "absolute",
    width: 30,
    height: 30,
    borderRadius: 15,
  },
  sparkle: {
    position: "absolute",
    fontSize: 18,
  },
  successContainer: {
    position: "absolute",
    bottom: "35%",
  },
  successText: {
    fontSize: 18,
    fontWeight: "800",
    textAlign: "center",
  },
});

export default memo(DropAnimationComponent);
