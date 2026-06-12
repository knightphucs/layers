/**
 * LAYERS — BadgeGrid
 * A grid of badges (unlocked in color, locked greyed out). Drop into the
 * Profile screen. Fetches on mount via badgeStore.
 */

import React, { useEffect } from "react";
import { View, Text, StyleSheet } from "react-native";
import { Colors } from "../../constants/colors";
import { useAuthStore } from "../../store/authStore";
import { useBadgeStore } from "../../store/badgeStore";
import { BadgeItem } from "../../types/gamification";

function BadgeCell({
  badge,
  textColor,
  subColor,
}: {
  badge: BadgeItem;
  textColor: string;
  subColor: string;
}) {
  return (
    <View style={styles.cell}>
      <Text style={[styles.icon, { opacity: badge.unlocked ? 1 : 0.25 }]}>
        {badge.icon}
      </Text>
      <Text
        style={[styles.title, { color: badge.unlocked ? textColor : subColor }]}
        numberOfLines={1}
      >
        {badge.title}
      </Text>
    </View>
  );
}

function BadgeGridBase() {
  const layer = useAuthStore((s) => s.layer);
  const theme = Colors[layer.toLowerCase() as "light" | "shadow"];
  const { badges, unlockedCount, total, fetch } = useBadgeStore();

  useEffect(() => {
    fetch();
  }, [fetch]);

  const textColor = theme?.text ?? "#fff";
  const subColor = theme?.textSecondary ?? "#9AA0B5";

  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={[styles.heading, { color: textColor }]}>Badges</Text>
        <Text style={[styles.counter, { color: subColor }]}>
          {unlockedCount}/{total}
        </Text>
      </View>

      <View style={styles.grid}>
        {badges.map((b) => (
          <BadgeCell
            key={b.id}
            badge={b}
            textColor={textColor}
            subColor={subColor}
          />
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { marginTop: 16 },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "baseline",
    marginBottom: 12,
  },
  heading: { fontSize: 18, fontWeight: "700" },
  counter: { fontSize: 14 },
  grid: { flexDirection: "row", flexWrap: "wrap" },
  cell: { width: "25%", alignItems: "center", marginBottom: 16 },
  icon: { fontSize: 34 },
  title: {
    fontSize: 11,
    marginTop: 4,
    textAlign: "center",
    paddingHorizontal: 2,
  },
});

export const BadgeGrid = React.memo(BadgeGridBase);
export default BadgeGrid;
