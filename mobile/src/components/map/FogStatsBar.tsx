/**
 * LAYERS - Fog Stats Bar
 * ====================================
 * Compact bar at the top of the map showing:
 *   - Fog percentage in current view
 *   - Total area explored
 *   - "New chunk!" flash when fog clears
 *
 * Appears below the layer toggle, fades in/out with map interaction.
 */

import React, { useEffect, useRef, memo } from "react";
import { View, Text, StyleSheet, Animated, Platform } from "react-native";
import { useAuthStore } from "../../store/authStore";
import { Colors } from "../../constants/colors";

interface Props {
  fogPercentage: number; // 0-100, how much is still fogged
  totalExplored: number; // Total chunks explored (all time)
  newChunkFlash: boolean; // Flash when new chunk explored
}

function FogStatsBarComponent({
  fogPercentage,
  totalExplored,
  newChunkFlash,
}: Props) {
  const { layer } = useAuthStore();
  const isShadow = layer === "SHADOW";
  const colors = Colors[isShadow ? "shadow" : "light"];

  // Flash animation for new chunk discovery
  const flashAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (newChunkFlash) {
      Animated.sequence([
        Animated.timing(flashAnim, {
          toValue: 1,
          duration: 200,
          useNativeDriver: true,
        }),
        Animated.timing(flashAnim, {
          toValue: 0,
          duration: 1500,
          useNativeDriver: true,
        }),
      ]).start();
    }
  }, [newChunkFlash]);

  // Explored percentage (inverse of fog)
  const exploredPct = Math.round(100 - fogPercentage);

  // Format area
  const areaSqKm = ((totalExplored * 100 * 100) / 1_000_000).toFixed(2);

  return (
    <View
      style={[styles.container, { backgroundColor: colors.surface + "E6" }]}
    >
      {/* Fog progress bar */}
      <View style={styles.progressRow}>
        <Text style={[styles.fogIcon]}>{isShadow ? "🌑" : "🌫️"}</Text>
        <View style={styles.progressBar}>
          <View
            style={[
              styles.progressFill,
              {
                width: `${exploredPct}%`,
                backgroundColor: isShadow ? "#8B5CF6" : "#3B82F6",
              },
            ]}
          />
        </View>
        <Text style={[styles.pctText, { color: colors.primary }]}>
          {exploredPct}%
        </Text>
      </View>

      {/* Stats row */}
      <View style={styles.statsRow}>
        <Text style={[styles.statText, { color: colors.textSecondary }]}>
          🗺️ {areaSqKm} km² explored
        </Text>
        <Text style={[styles.statText, { color: colors.textSecondary }]}>
          {totalExplored} chunks
        </Text>
      </View>

      {/* New chunk flash */}
      <Animated.View
        style={[
          styles.flashOverlay,
          {
            opacity: flashAnim,
            backgroundColor: isShadow
              ? "rgba(139, 92, 246, 0.3)"
              : "rgba(59, 130, 246, 0.3)",
          },
        ]}
        pointerEvents="none"
      >
        <Text style={styles.flashText}>
          {isShadow ? "✨ Fog cleared!" : "🗺️ New area!"}
        </Text>
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    borderRadius: 12,
    padding: 8,
    paddingHorizontal: 12,
    overflow: "hidden",
  },
  progressRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  fogIcon: {
    fontSize: 14,
  },
  progressBar: {
    flex: 1,
    height: 6,
    backgroundColor: "rgba(128, 128, 128, 0.2)",
    borderRadius: 3,
    overflow: "hidden",
  },
  progressFill: {
    height: "100%",
    borderRadius: 3,
  },
  pctText: {
    fontSize: 12,
    fontWeight: "700",
    minWidth: 32,
    textAlign: "right",
  },
  statsRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginTop: 4,
  },
  statText: {
    fontSize: 10,
  },
  flashOverlay: {
    ...StyleSheet.absoluteFillObject,
    borderRadius: 12,
    alignItems: "center",
    justifyContent: "center",
  },
  flashText: {
    color: "#FFF",
    fontWeight: "bold",
    fontSize: 14,
  },
});

export default memo(FogStatsBarComponent);
