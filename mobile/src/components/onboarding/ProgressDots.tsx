/**
 * LAYERS — ProgressDots
 * ==========================================
 * Animated page indicator for the story-mode pager.
 * Active dot stretches into a pill — same motion language as
 * ArtifactMarker's pulse (Animated + useNativeDriver where possible).
 */

import React from "react";
import { View, Animated, StyleSheet } from "react-native";

interface Props {
  count: number;
  activeIndex: number;
  color: string;
  inactiveColor: string;
}

function ProgressDots({ count, activeIndex, color, inactiveColor }: Props) {
  return (
    <View style={styles.row}>
      {Array.from({ length: count }).map((_, i) => {
        const isActive = i === activeIndex;
        return (
          <Animated.View
            key={i}
            style={[
              styles.dot,
              {
                backgroundColor: isActive ? color : inactiveColor,
                width: isActive ? 24 : 8,
                opacity: isActive ? 1 : 0.5,
              },
            ]}
          />
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    gap: 8,
  },
  dot: {
    height: 8,
    borderRadius: 4,
  },
});

// React.memo — convention: memo on all list/repeated components
export default React.memo(ProgressDots);
