/**
 * LAYERS - Offline Banner Component
 * Shows a persistent banner when internet is unavailable
 * Auto-hides when connection returns with a "Back online!" message
 *
 * USAGE: Place <OfflineBanner /> in your root layout (App.tsx)
 */

import React, { useState, useEffect, useRef } from "react";
import { View, Text, StyleSheet, Animated } from "react-native";
import { useNetworkStatus } from "../hooks/useNetworkStatus";

export default function OfflineBanner() {
  const { isConnected } = useNetworkStatus();
  const [showReconnected, setShowReconnected] = useState(false);
  const slideAnim = useRef(new Animated.Value(-50)).current;
  const wasOffline = useRef(false);

  useEffect(() => {
    if (!isConnected) {
      // Slide down to show "Offline"
      wasOffline.current = true;
      Animated.spring(slideAnim, {
        toValue: 0,
        useNativeDriver: true,
        tension: 80,
        friction: 12,
      }).start();
    } else if (wasOffline.current) {
      // Show "Back online!" briefly
      setShowReconnected(true);
      setTimeout(() => {
        Animated.timing(slideAnim, {
          toValue: -50,
          duration: 300,
          useNativeDriver: true,
        }).start(() => {
          setShowReconnected(false);
          wasOffline.current = false;
        });
      }, 2000);
    }
  }, [isConnected]);

  if (isConnected && !showReconnected) return null;

  return (
    <Animated.View
      style={[
        styles.container,
        {
          transform: [{ translateY: slideAnim }],
          backgroundColor: isConnected ? "#10B981" : "#EF4444",
        },
      ]}
    >
      <Text style={styles.icon}>{isConnected ? "✅" : "📡"}</Text>
      <Text style={styles.text}>
        {isConnected ? "Back online!" : "No internet connection"}
      </Text>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  container: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    zIndex: 9999,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    paddingTop: 50, // Safe area
    paddingBottom: 8,
    paddingHorizontal: 16,
  },
  icon: {
    fontSize: 14,
    marginRight: 8,
  },
  text: {
    color: "#FFFFFF",
    fontSize: 13,
    fontWeight: "600",
  },
});
