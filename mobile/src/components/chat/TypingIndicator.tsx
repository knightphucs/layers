/**
 * LAYERS — TypingIndicator
 * =========================================
 * Animated "X is typing…" indicator. Pulls from chatStore.typingUsersByRoom,
 * which is updated by the WS frame handler.
 *
 * Drop at the top of MessageInput (above the input field).
 */

import React, { useEffect, useRef } from "react";
import { View, Text, StyleSheet, Animated, Easing } from "react-native";
import { Colors } from "../../constants/colors";
import { useAuthStore } from "../../store/authStore";
import { useChatStore } from "../../store/chatStore";

interface TypingIndicatorProps {
  roomId: string;
}

function Dot({ delay }: { delay: number }) {
  const opacity = useRef(new Animated.Value(0.3)).current;

  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(opacity, {
          toValue: 1,
          duration: 400,
          delay,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
        Animated.timing(opacity, {
          toValue: 0.3,
          duration: 400,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [opacity, delay]);

  return <Animated.View style={[styles.dot, { opacity }]} />;
}

function TypingIndicatorComponent({ roomId }: TypingIndicatorProps) {
  const layer = useAuthStore((s) => s.layer);
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];

  // typingUsersByRoom is a Record<roomId, Set<userId>> in the store
  const typingUserCount = useChatStore((s) => {
    const set = s.typingUsersByRoom?.[roomId];
    return set ? set.size : 0;
  });

  if (typingUserCount === 0) return null;

  const label =
    typingUserCount === 1
      ? "Someone is typing"
      : `${typingUserCount} people are typing`;

  return (
    <View style={[styles.container, { backgroundColor: colors.surface }]}>
      <Text style={[styles.text, { color: colors.textSecondary }]}>
        {label}
      </Text>
      <View style={styles.dotsRow}>
        <Dot delay={0} />
        <Dot delay={150} />
        <Dot delay={300} />
      </View>
    </View>
  );
}

export const TypingIndicator = React.memo(TypingIndicatorComponent);
TypingIndicator.displayName = "TypingIndicator";

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 14,
    paddingVertical: 4,
    gap: 6,
    alignSelf: "flex-start",
    marginLeft: 12,
    marginBottom: 4,
    borderRadius: 12,
  },
  text: {
    fontSize: 12,
    fontStyle: "italic",
  },
  dotsRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 3,
    marginLeft: 2,
  },
  dot: {
    width: 5,
    height: 5,
    borderRadius: 2.5,
    backgroundColor: "#94A3B8",
  },
});

export default TypingIndicator;
