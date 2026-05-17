/**
 * LAYERS — CampfireBeacon Component
 * ==================================================
 * A map marker for an active campfire. Renders as a child of <Marker>
 * inside MapScreen's <MapView>.
 *
 * - Pulsing flame animation (same Animated.loop pattern as MapScreen's user marker)
 * - Member count badge showing online_count
 * - Tap → onPress(campfire.id)
 *
 * PATTERN: React.memo. Uses Colors[layer] theming.
 *
 * USAGE (inside MapScreen's MapView):
 *   {nearbyCampfires.map((c) => (
 *     <CampfireBeacon key={c.id} campfire={c} onPress={handleOpenCampfire} />
 *   ))}
 */

import React, { useRef, useEffect } from "react";
import { View, Text, StyleSheet, Animated } from "react-native";
import { Marker } from "react-native-maps";
import { Colors } from "../../constants/colors";
import { useAuthStore } from "../../store/authStore";
import { CampfireNearbyItem } from "../../types/chat";

interface CampfireBeaconProps {
  campfire: CampfireNearbyItem;
  onPress: (roomId: string) => void;
}

function CampfireBeaconComponent({ campfire, onPress }: CampfireBeaconProps) {
  const layer = useAuthStore((s) => s.layer);
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];

  const pulseAnim = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    const pulse = Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, {
          toValue: 1.4,
          duration: 1200,
          useNativeDriver: true,
        }),
        Animated.timing(pulseAnim, {
          toValue: 1,
          duration: 1200,
          useNativeDriver: true,
        }),
      ]),
    );
    pulse.start();
    return () => pulse.stop();
  }, [pulseAnim]);

  return (
    <Marker
      coordinate={{
        latitude: campfire.center_latitude,
        longitude: campfire.center_longitude,
      }}
      anchor={{ x: 0.5, y: 0.5 }}
      onPress={() => onPress(campfire.id)}
      tracksViewChanges={false}
    >
      <View style={styles.container}>
        {/* Pulsing glow ring */}
        <Animated.View
          style={[
            styles.glow,
            {
              backgroundColor: "rgba(249, 115, 22, 0.25)",
              transform: [{ scale: pulseAnim }],
            },
          ]}
        />
        {/* Flame core */}
        <View style={[styles.core, { borderColor: colors.surface }]}>
          <Text style={styles.flame}>🔥</Text>
        </View>
        {/* Online count badge */}
        {campfire.online_count > 0 && (
          <View style={[styles.badge, { backgroundColor: colors.primary }]}>
            <Text style={styles.badgeText}>{campfire.online_count}</Text>
          </View>
        )}
      </View>
    </Marker>
  );
}

export const CampfireBeacon = React.memo(CampfireBeaconComponent);
CampfireBeacon.displayName = "CampfireBeacon";

const styles = StyleSheet.create({
  container: {
    width: 48,
    height: 48,
    alignItems: "center",
    justifyContent: "center",
  },
  glow: {
    position: "absolute",
    width: 44,
    height: 44,
    borderRadius: 22,
  },
  core: {
    width: 34,
    height: 34,
    borderRadius: 17,
    backgroundColor: "#F97316",
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 2,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 3,
    elevation: 4,
  },
  flame: {
    fontSize: 18,
  },
  badge: {
    position: "absolute",
    top: -2,
    right: -2,
    minWidth: 18,
    height: 18,
    borderRadius: 9,
    paddingHorizontal: 4,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1.5,
    borderColor: "#FFFFFF",
  },
  badgeText: {
    color: "#FFFFFF",
    fontSize: 10,
    fontWeight: "700",
  },
});

export default CampfireBeacon;
