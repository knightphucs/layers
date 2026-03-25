/**
 * LAYERS - Fog Clear Animation
 * ===================================
 * The SATISFYING moment when fog clears as you walk.
 * This is the dopamine hit that keeps users exploring.
 *
 * EFFECT:
 *   1. Burst of particles at the newly cleared chunk
 *   2. Brief bright flash at the edges
 *   3. Scale-in reveal animation
 *   4. Haptic feedback (medium impact)
 *
 * Triggers when useExploration detects is_new=true from backend.
 * Renders at the GPS coordinates of the newly explored chunk center.
 */

import React, { useEffect, useRef, memo } from "react";
import { View, StyleSheet, Animated, Easing, Platform } from "react-native";
import * as Haptics from "expo-haptics";
import { useAuthStore } from "../../store/authStore";

// ============================================================
// TYPES
// ============================================================

interface ClearEvent {
  id: string; // Unique ID for this clear event
  latitude: number;
  longitude: number;
  timestamp: number;
}

interface Props {
  /** The most recent fog clear event to animate */
  clearEvent: ClearEvent | null;
}

// ============================================================
// PARTICLE CONFIG
// ============================================================

const PARTICLE_COUNT = 8;
const ANIMATION_DURATION = 800; // ms

/** Generate evenly-spaced angles for particle burst */
function getParticleAngles(count: number): number[] {
  return Array.from({ length: count }, (_, i) => (i / count) * Math.PI * 2);
}

// ============================================================
// COMPONENT
// ============================================================

function FogClearAnimationComponent({ clearEvent }: Props) {
  const { layer } = useAuthStore();
  const isShadow = layer === "SHADOW";

  // Animation values
  const burstScale = useRef(new Animated.Value(0)).current;
  const burstOpacity = useRef(new Animated.Value(0)).current;
  const flashOpacity = useRef(new Animated.Value(0)).current;
  const ringScale = useRef(new Animated.Value(0.3)).current;
  const ringOpacity = useRef(new Animated.Value(0)).current;

  // Particle animations (one per particle)
  const particleAnims = useRef(
    Array.from({ length: PARTICLE_COUNT }, () => ({
      translateX: new Animated.Value(0),
      translateY: new Animated.Value(0),
      opacity: new Animated.Value(0),
      scale: new Animated.Value(0),
    })),
  ).current;

  const angles = useRef(getParticleAngles(PARTICLE_COUNT)).current;

  useEffect(() => {
    if (!clearEvent) return;

    // Haptic feedback — the physical "thud" of discovery
    if (Platform.OS !== "web") {
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    }

    // Reset all values
    burstScale.setValue(0);
    burstOpacity.setValue(1);
    flashOpacity.setValue(1);
    ringScale.setValue(0.3);
    ringOpacity.setValue(1);
    particleAnims.forEach((p) => {
      p.translateX.setValue(0);
      p.translateY.setValue(0);
      p.opacity.setValue(1);
      p.scale.setValue(1);
    });

    // ---- ANIMATION SEQUENCE ----

    // 1. Central flash burst
    const flashAnimation = Animated.sequence([
      Animated.timing(flashOpacity, {
        toValue: 0.8,
        duration: 100,
        useNativeDriver: true,
      }),
      Animated.timing(flashOpacity, {
        toValue: 0,
        duration: 400,
        useNativeDriver: true,
      }),
    ]);

    // 2. Expanding ring
    const ringAnimation = Animated.parallel([
      Animated.timing(ringScale, {
        toValue: 2.5,
        duration: 600,
        easing: Easing.out(Easing.cubic),
        useNativeDriver: true,
      }),
      Animated.timing(ringOpacity, {
        toValue: 0,
        duration: 600,
        easing: Easing.in(Easing.quad),
        useNativeDriver: true,
      }),
    ]);

    // 3. Particle burst — each particle flies outward from center
    const particleAnimations = particleAnims.map((p, i) => {
      const angle = angles[i];
      const distance = 35 + Math.random() * 20; // Spread radius

      return Animated.parallel([
        Animated.timing(p.translateX, {
          toValue: Math.cos(angle) * distance,
          duration: ANIMATION_DURATION,
          easing: Easing.out(Easing.cubic),
          useNativeDriver: true,
        }),
        Animated.timing(p.translateY, {
          toValue: Math.sin(angle) * distance,
          duration: ANIMATION_DURATION,
          easing: Easing.out(Easing.cubic),
          useNativeDriver: true,
        }),
        Animated.sequence([
          Animated.delay(200),
          Animated.timing(p.opacity, {
            toValue: 0,
            duration: ANIMATION_DURATION - 200,
            useNativeDriver: true,
          }),
        ]),
        Animated.sequence([
          Animated.timing(p.scale, {
            toValue: 1.3,
            duration: 200,
            useNativeDriver: true,
          }),
          Animated.timing(p.scale, {
            toValue: 0,
            duration: ANIMATION_DURATION - 200,
            useNativeDriver: true,
          }),
        ]),
      ]);
    });

    // 4. Central burst scale
    const burstAnimation = Animated.parallel([
      Animated.timing(burstScale, {
        toValue: 1.5,
        duration: 500,
        easing: Easing.out(Easing.back(1.5)),
        useNativeDriver: true,
      }),
      Animated.sequence([
        Animated.delay(300),
        Animated.timing(burstOpacity, {
          toValue: 0,
          duration: 300,
          useNativeDriver: true,
        }),
      ]),
    ]);

    // Run all in parallel
    Animated.parallel([
      flashAnimation,
      ringAnimation,
      burstAnimation,
      ...particleAnimations,
    ]).start();
  }, [clearEvent?.id]);

  if (!clearEvent) return null;

  const accentColor = isShadow ? "#8B5CF6" : "#3B82F6";
  const particleColor = isShadow ? "#C4B5FD" : "#93C5FD";

  return (
    <View style={styles.container} pointerEvents="none">
      {/* Central flash */}
      <Animated.View
        style={[
          styles.flash,
          {
            opacity: flashOpacity,
            backgroundColor: accentColor,
          },
        ]}
      />

      {/* Expanding ring */}
      <Animated.View
        style={[
          styles.ring,
          {
            borderColor: accentColor,
            opacity: ringOpacity,
            transform: [{ scale: ringScale }],
          },
        ]}
      />

      {/* Central burst icon */}
      <Animated.View
        style={[
          styles.burstCenter,
          {
            opacity: burstOpacity,
            transform: [{ scale: burstScale }],
          },
        ]}
      >
        <View style={styles.burstIcon}>
          <View style={[styles.burstDot, { backgroundColor: accentColor }]} />
        </View>
      </Animated.View>

      {/* Particles */}
      {particleAnims.map((p, i) => (
        <Animated.View
          key={i}
          style={[
            styles.particle,
            {
              backgroundColor: particleColor,
              opacity: p.opacity,
              transform: [
                { translateX: p.translateX },
                { translateY: p.translateY },
                { scale: p.scale },
              ],
            },
          ]}
        />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    position: "absolute",
    width: 100,
    height: 100,
    alignItems: "center",
    justifyContent: "center",
  },
  flash: {
    position: "absolute",
    width: 40,
    height: 40,
    borderRadius: 20,
  },
  ring: {
    position: "absolute",
    width: 50,
    height: 50,
    borderRadius: 25,
    borderWidth: 2.5,
    backgroundColor: "transparent",
  },
  burstCenter: {
    position: "absolute",
    alignItems: "center",
    justifyContent: "center",
  },
  burstIcon: {
    width: 24,
    height: 24,
    borderRadius: 12,
    alignItems: "center",
    justifyContent: "center",
  },
  burstDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
  },
  particle: {
    position: "absolute",
    width: 6,
    height: 6,
    borderRadius: 3,
  },
});

export default memo(FogClearAnimationComponent);
