/**
 * LAYERS — LeaderboardScreen
 * Global / Weekly tabs, ranked list, your rank pinned at the bottom.
 */

import React, { useCallback, useEffect } from "react";
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  RefreshControl,
  ActivityIndicator,
  Pressable,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { Colors } from "../../constants/colors";
import { useAuthStore } from "../../store/authStore";
import { useLeaderboardStore } from "../../store/leaderboardStore";
import { LeaderboardRow } from "../../components/gamification/LeaderboardRow";
import { LeaderboardEntry, LeaderboardScope } from "../../types/gamification";

const TABS: { key: LeaderboardScope; label: string }[] = [
  { key: "global", label: "All-time" },
  { key: "weekly", label: "This week" },
];

export default function LeaderboardScreen() {
  const layer = useAuthStore((s) => s.layer);
  const theme = Colors[layer.toLowerCase() as "light" | "shadow"];

  const { scope, entries, myRank, myScore, isLoading, error, setScope, fetch } =
    useLeaderboardStore();

  useEffect(() => {
    fetch();
  }, [fetch]);

  const renderItem = useCallback(
    ({ item }: { item: LeaderboardEntry }) => <LeaderboardRow entry={item} />,
    [],
  );
  const keyExtractor = useCallback(
    (item: LeaderboardEntry) => item.user_id,
    [],
  );

  const bg = theme?.background ?? "#0E0E1A";
  const textColor = theme?.text ?? "#fff";
  const accent = theme?.primary ?? "#6C8EFF";

  return (
    <SafeAreaView
      style={[styles.container, { backgroundColor: bg }]}
      edges={["top"]}
    >
      <Text style={[styles.heading, { color: textColor }]}>Leaderboard</Text>

      {/* Tabs */}
      <View style={styles.tabs}>
        {TABS.map((t) => {
          const active = scope === t.key;
          return (
            <Pressable
              key={t.key}
              onPress={() => setScope(t.key)}
              style={[
                styles.tab,
                {
                  backgroundColor: active ? accent : "transparent",
                  borderColor: active
                    ? accent
                    : (theme?.border ?? "rgba(255,255,255,0.12)"),
                },
              ]}
            >
              <Text
                style={[styles.tabText, { color: active ? "#fff" : textColor }]}
              >
                {t.label}
              </Text>
            </Pressable>
          );
        })}
      </View>

      {isLoading && entries.length === 0 ? (
        <View style={styles.center}>
          <ActivityIndicator size="large" color={accent} />
        </View>
      ) : error && entries.length === 0 ? (
        <View style={styles.center}>
          <Text style={[styles.muted, { color: textColor }]}>{error}</Text>
          <Text
            style={[styles.retry, { color: accent }]}
            onPress={() => fetch()}
          >
            Tap to retry
          </Text>
        </View>
      ) : (
        <FlatList
          data={entries}
          renderItem={renderItem}
          keyExtractor={keyExtractor}
          contentContainerStyle={styles.list}
          refreshControl={
            <RefreshControl
              refreshing={isLoading}
              onRefresh={fetch}
              tintColor={accent}
            />
          }
          ListEmptyComponent={
            <View style={styles.center}>
              <Text
                style={[
                  styles.muted,
                  { color: theme?.textSecondary ?? "#9AA0B5" },
                ]}
              >
                No rankings yet. Earn some XP!
              </Text>
            </View>
          }
        />
      )}

      {/* Your rank pinned */}
      <View
        style={[
          styles.meBar,
          {
            backgroundColor: theme?.card ?? "#1B1B2F",
            borderTopColor: theme?.border ?? "rgba(255,255,255,0.08)",
          },
        ]}
      >
        <Text
          style={[styles.meLabel, { color: theme?.textSecondary ?? "#9AA0B5" }]}
        >
          Your rank
        </Text>
        <Text style={[styles.meRank, { color: textColor }]}>
          {myRank ? `#${myRank}` : "Unranked"}
        </Text>
        <Text style={[styles.meScore, { color: accent }]}>
          {myScore.toLocaleString()} XP
        </Text>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  heading: {
    fontSize: 26,
    fontWeight: "800",
    paddingHorizontal: 20,
    paddingTop: 8,
  },
  tabs: {
    flexDirection: "row",
    paddingHorizontal: 20,
    paddingVertical: 12,
    gap: 10,
  },
  tab: {
    paddingVertical: 8,
    paddingHorizontal: 18,
    borderRadius: 20,
    borderWidth: 1,
  },
  tabText: { fontSize: 14, fontWeight: "600" },
  list: { paddingHorizontal: 20, paddingBottom: 20 },
  center: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    padding: 40,
    minHeight: 200,
  },
  muted: { fontSize: 15, textAlign: "center" },
  retry: { fontSize: 14, fontWeight: "600", marginTop: 12 },
  meBar: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 14,
    paddingHorizontal: 20,
    borderTopWidth: 1,
  },
  meLabel: { fontSize: 13, flex: 1 },
  meRank: { fontSize: 16, fontWeight: "800", marginRight: 14 },
  meScore: { fontSize: 15, fontWeight: "700" },
});
