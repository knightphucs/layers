/**
 * LAYERS — LeaderboardRow
 * One row: rank (medal for top 3), avatar/initial, username, score.
 * Highlights the current user. React.memo for FlatList performance.
 */

import React from "react";
import { View, Text, Image, StyleSheet } from "react-native";
import { Colors } from "../../constants/colors";
import { useAuthStore } from "../../store/authStore";
import { LeaderboardEntry } from "../../types/gamification";

interface Props {
  entry: LeaderboardEntry;
}

const MEDALS: Record<number, string> = { 1: "🥇", 2: "🥈", 3: "🥉" };

function LeaderboardRowBase({ entry }: Props) {
  const layer = useAuthStore((s) => s.layer);
  const theme = Colors[layer.toLowerCase() as "light" | "shadow"];

  const highlight = entry.is_me;
  const accent = theme?.primary ?? "#6C8EFF";

  return (
    <View
      style={[
        styles.row,
        {
          backgroundColor: highlight
            ? accent + "22"
            : (theme?.card ?? theme?.surface ?? "#1B1B2F"),
          borderColor: highlight
            ? accent
            : (theme?.border ?? "rgba(255,255,255,0.06)"),
        },
      ]}
    >
      <View style={styles.rankWrap}>
        <Text style={[styles.rank, { color: theme?.text ?? "#fff" }]}>
          {MEDALS[entry.rank] ?? `#${entry.rank}`}
        </Text>
      </View>

      {entry.avatar_url ? (
        <Image source={{ uri: entry.avatar_url }} style={styles.avatar} />
      ) : (
        <View
          style={[
            styles.avatar,
            styles.avatarFallback,
            { backgroundColor: accent },
          ]}
        >
          <Text style={styles.avatarInitial}>
            {entry.username?.charAt(0).toUpperCase() ?? "?"}
          </Text>
        </View>
      )}

      <Text
        style={[
          styles.name,
          {
            color: theme?.text ?? "#fff",
            fontWeight: highlight ? "800" : "600",
          },
        ]}
        numberOfLines={1}
      >
        {entry.username}
        {highlight ? "  (you)" : ""}
      </Text>

      <View style={styles.scoreWrap}>
        <Text style={[styles.score, { color: accent }]}>
          {entry.score.toLocaleString()}
        </Text>
        <Text
          style={[
            styles.scoreUnit,
            { color: theme?.textSecondary ?? "#9AA0B5" },
          ]}
        >
          XP
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: "row",
    alignItems: "center",
    borderRadius: 14,
    borderWidth: 1,
    paddingVertical: 10,
    paddingHorizontal: 12,
    marginBottom: 8,
  },
  rankWrap: { width: 40, alignItems: "center" },
  rank: { fontSize: 16, fontWeight: "700" },
  avatar: { width: 36, height: 36, borderRadius: 18, marginHorizontal: 10 },
  avatarFallback: { alignItems: "center", justifyContent: "center" },
  avatarInitial: { color: "#fff", fontWeight: "700", fontSize: 16 },
  name: { flex: 1, fontSize: 15 },
  scoreWrap: { flexDirection: "row", alignItems: "baseline", marginLeft: 8 },
  score: { fontSize: 16, fontWeight: "800" },
  scoreUnit: { fontSize: 10, marginLeft: 3, letterSpacing: 1 },
});

export const LeaderboardRow = React.memo(LeaderboardRowBase);
export default LeaderboardRow;
