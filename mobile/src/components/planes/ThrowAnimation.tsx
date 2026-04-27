/**
 * LAYERS — ThrowAnimation Component
 * ==========================================
 * Animated paper plane flying across the screen.
 * Triggered after a successful throw API call.
 *
 * Animation phases:
 *   1. Scale up + fade in (300ms)
 *   2. Curved flight path across screen (1800ms)
 *   3. Fade out + celebration dots (500ms)
 */

import React, { useEffect, useRef } from "react";
import {
  View,
  Text,
  StyleSheet,
  Animated,
  Dimensions,
  Easing,
} from "react-native";

const { width: SCREEN_W, height: SCREEN_H } = Dimensions.get("window");

interface ThrowAnimationProps {
  onComplete?: () => void;
  landingDistance: number; // meters — shown as readout
}

export default function ThrowAnimation({
  onComplete,
  landingDistance,
}: ThrowAnimationProps) {
  const translateX = useRef(new Animated.Value(0)).current;
  const translateY = useRef(new Animated.Value(0)).current;
  const scale = useRef(new Animated.Value(0.3)).current;
  const rotate = useRef(new Animated.Value(0)).current;
  const opacity = useRef(new Animated.Value(0)).current;
  const textOpacity = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const flightDuration = 1800;

    Animated.sequence([
      // Phase 1: Appear + scale up
      Animated.parallel([
        Animated.timing(opacity, {
          toValue: 1,
          duration: 300,
          useNativeDriver: true,
        }),
        Animated.spring(scale, {
          toValue: 1.2,
          friction: 4,
          useNativeDriver: true,
        }),
      ]),
      // Phase 2: Fly across screen in a curve
      Animated.parallel([
        Animated.timing(translateX, {
          toValue: SCREEN_W * 0.8,
          duration: flightDuration,
          easing: Easing.out(Easing.quad),
          useNativeDriver: true,
        }),
        Animated.timing(translateY, {
          toValue: -SCREEN_H * 0.3,
          duration: flightDuration,
          easing: Easing.inOut(Easing.cubic),
          useNativeDriver: true,
        }),
        Animated.timing(rotate, {
          toValue: 1,
          duration: flightDuration,
          easing: Easing.inOut(Easing.quad),
          useNativeDriver: true,
        }),
        Animated.timing(scale, {
          toValue: 0.5,
          duration: flightDuration,
          easing: Easing.out(Easing.quad),
          useNativeDriver: true,
        }),
        Animated.sequence([
          Animated.delay(flightDuration - 400),
          Animated.timing(textOpacity, {
            toValue: 1,
            duration: 300,
            useNativeDriver: true,
          }),
        ]),
      ]),
      // Phase 3: Fade out
      Animated.parallel([
        Animated.timing(opacity, {
          toValue: 0,
          duration: 500,
          useNativeDriver: true,
        }),
        Animated.delay(1500),
      ]),
    ]).start(() => {
      onComplete?.();
    });
  }, []);

  const rotation = rotate.interpolate({
    inputRange: [0, 1],
    outputRange: ["0deg", "25deg"],
  });

  return (
    <View style={styles.container} pointerEvents="none">
      {/* Flying plane */}
      <Animated.View
        style={[
          styles.plane,
          {
            opacity,
            transform: [
              { translateX },
              { translateY },
              { scale },
              { rotate: rotation },
            ],
          },
        ]}
      >
        <Text style={styles.planeEmoji}>✈️</Text>
      </Animated.View>

      {/* Landing readout */}
      <Animated.View style={[styles.readout, { opacity: textOpacity }]}>
        <Text style={styles.readoutIcon}>📍</Text>
        <Text style={styles.readoutText}>
          Landed {Math.round(landingDistance)}m away!
        </Text>
        <Text style={styles.readoutSub}>Someone will find it soon...</Text>
      </Animated.View>
    </View>
  );
}

// ============================================================
// STYLES
// ============================================================

const styles = StyleSheet.create({
  container: {
    ...StyleSheet.absoluteFillObject,
    zIndex: 1000,
    justifyContent: "center",
    alignItems: "center",
  },
  plane: {
    position: "absolute",
    left: SCREEN_W * 0.1,
    top: SCREEN_H * 0.5,
  },
  planeEmoji: {
    fontSize: 72,
  },
  readout: {
    position: "absolute",
    top: "30%",
    alignItems: "center",
    backgroundColor: "rgba(0,0,0,0.75)",
    paddingHorizontal: 24,
    paddingVertical: 16,
    borderRadius: 14,
  },
  readoutIcon: {
    fontSize: 32,
    marginBottom: 6,
  },
  readoutText: {
    color: "#FFFFFF",
    fontSize: 17,
    fontWeight: "700",
    marginBottom: 4,
  },
  readoutSub: {
    color: "#FFFFFF",
    opacity: 0.8,
    fontSize: 13,
  },
});
