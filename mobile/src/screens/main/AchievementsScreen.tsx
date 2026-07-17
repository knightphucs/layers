/**
 * LAYERS — AchievementsScreen
 * ==========================================
 * Full-screen achievements view — closes the "Coming in Week 7!" alert
 * in ProfileScreen (the backend has been live since Week 7 😄).
 *
 * PATTERN: render-guard sub-screen with onBack prop, same as
 * ConnectionsScreen / TimeCapsuleScreen inside ProfileScreen.
 *
 * FEATURES:
 *   - Progress header (unlocked/total + bar)
 *   - Badge rows with description + unlock date
 *   - "Check for new badges" → POST /badges/sync → celebratory toast-ish
 */

import React, { useEffect, useState, useCallback } from "react";
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
  StyleSheet,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { useAuthStore } from "../../store/authStore";
import { useBadgeStore } from "../../store/badgeStore";
import { Colors } from "../../constants/colors";
import { BadgeItem } from "../../types/gamification";

interface Props {
  onBack: () => void;
}

// ============================================================
// BADGE ROW
// ============================================================

const BadgeRow = React.memo(function BadgeRow({
  badge,
  colors,
}: {
  badge: BadgeItem;
  colors: any;
}) {
  const unlockedDate = badge.unlocked_at
    ? new Date(badge.unlocked_at).toLocaleDateString("vi-VN", {
        year: "numeric",
        month: "short",
        day: "numeric",
      })
    : null;

  return (
    <View
      style={[
        styles.row,
        {
          backgroundColor: colors.surface ?? colors.background,
          borderColor: badge.unlocked
            ? colors.primary
            : (colors.border ?? "rgba(128,128,128,0.25)"),
          opacity: badge.unlocked ? 1 : 0.65,
        },
      ]}
    >
      <Text style={[styles.rowIcon, { opacity: badge.unlocked ? 1 : 0.3 }]}>
        {badge.icon}
      </Text>
      <View style={styles.rowContent}>
        <Text style={[styles.rowTitle, { color: colors.text }]}>
          {badge.title}
        </Text>
        <Text style={[styles.rowDesc, { color: colors.textSecondary }]}>
          {badge.description}
        </Text>
        {unlockedDate && (
          <Text style={[styles.rowDate, { color: colors.primary }]}>
            Unlocked {unlockedDate}
          </Text>
        )}
      </View>
      {badge.unlocked ? (
        <Text style={styles.rowCheck}>✅</Text>
      ) : (
        <Text style={[styles.rowLock, { color: colors.textSecondary }]}>🔒</Text>
      )}
    </View>
  );
});

// ============================================================
// SCREEN
// ============================================================

export default function AchievementsScreen({ onBack }: Props) {
  const { layer } = useAuthStore();
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];
  const { badges, unlockedCount, total, isLoading, fetch, sync } =
    useBadgeStore();

  const [isSyncing, setIsSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);

  useEffect(() => {
    fetch();
  }, [fetch]);

  const handleSync = useCallback(async () => {
    setIsSyncing(true);
    setSyncMessage(null);
    const newlyUnlocked = await sync();
    setIsSyncing(false);
    if (newlyUnlocked.length > 0) {
      setSyncMessage(
        `🎉 Unlocked: ${newlyUnlocked.map((b) => `${b.icon} ${b.title}`).join(", ")}`,
      );
    } else {
      setSyncMessage("You're all caught up — keep exploring! 🌆");
    }
  }, [sync]);

  const progress = total > 0 ? unlockedCount / total : 0;

  const renderItem = useCallback(
    ({ item }: { item: BadgeItem }) => <BadgeRow badge={item} colors={colors} />,
    [colors],
  );

  return (
    <SafeAreaView
      style={[styles.container, { backgroundColor: colors.background }]}
      edges={["top"]}
    >
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity
          onPress={onBack}
          hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}
          accessibilityRole="button"
          accessibilityLabel="Go back"
        >
          <Text style={[styles.backArrow, { color: colors.text }]}>←</Text>
        </TouchableOpacity>
        <Text style={[styles.headerTitle, { color: colors.text }]}>
          🏆 Achievements
        </Text>
        <View style={styles.headerSpacer} />
      </View>

      {/* Progress */}
      <View style={styles.progressWrap}>
        <Text style={[styles.progressLabel, { color: colors.textSecondary }]}>
          {unlockedCount} of {total} unlocked
        </Text>
        <View
          style={[
            styles.progressTrack,
            { backgroundColor: colors.border ?? "rgba(128,128,128,0.25)" },
          ]}
        >
          <View
            style={[
              styles.progressFill,
              { backgroundColor: colors.primary, width: `${progress * 100}%` },
            ]}
          />
        </View>
      </View>

      {/* Sync */}
      <TouchableOpacity
        style={[styles.syncButton, { borderColor: colors.primary }]}
        onPress={handleSync}
        disabled={isSyncing}
        accessibilityRole="button"
        accessibilityLabel="Check for new badges"
      >
        {isSyncing ? (
          <ActivityIndicator size="small" color={colors.primary} />
        ) : (
          <Text style={[styles.syncText, { color: colors.primary }]}>
            Check for new badges ✨
          </Text>
        )}
      </TouchableOpacity>
      {syncMessage && (
        <Text style={[styles.syncMessage, { color: colors.text }]}>
          {syncMessage}
        </Text>
      )}

      {/* Badge list */}
      {isLoading && badges.length === 0 ? (
        <View style={styles.loadingWrap}>
          <ActivityIndicator size="large" color={colors.primary} />
        </View>
      ) : (
        <FlatList
          data={badges}
          keyExtractor={(item) => item.id}
          renderItem={renderItem}
          contentContainerStyle={styles.list}
          showsVerticalScrollIndicator={false}
        />
      )}
    </SafeAreaView>
  );
}

// ============================================================
// STYLES
// ============================================================

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 20,
    paddingVertical: 12,
  },
  backArrow: { fontSize: 24, fontWeight: "600" },
  headerTitle: {
    flex: 1,
    fontSize: 20,
    fontWeight: "800",
    textAlign: "center",
  },
  headerSpacer: { width: 24 },
  progressWrap: { paddingHorizontal: 20, marginBottom: 12 },
  progressLabel: { fontSize: 13, marginBottom: 6 },
  progressTrack: { height: 8, borderRadius: 4, overflow: "hidden" },
  progressFill: { height: 8, borderRadius: 4 },
  syncButton: {
    marginHorizontal: 20,
    marginBottom: 8,
    borderWidth: 1.5,
    borderRadius: 22,
    paddingVertical: 10,
    alignItems: "center",
  },
  syncText: { fontSize: 14, fontWeight: "700" },
  syncMessage: {
    fontSize: 13,
    textAlign: "center",
    paddingHorizontal: 24,
    marginBottom: 8,
  },
  loadingWrap: { flex: 1, justifyContent: "center", alignItems: "center" },
  list: { paddingHorizontal: 20, paddingBottom: 24 },
  row: {
    flexDirection: "row",
    alignItems: "center",
    borderWidth: 1,
    borderRadius: 16,
    padding: 14,
    marginBottom: 10,
    gap: 12,
  },
  rowIcon: { fontSize: 30 },
  rowContent: { flex: 1 },
  rowTitle: { fontSize: 15, fontWeight: "700" },
  rowDesc: { fontSize: 12, lineHeight: 17, marginTop: 2 },
  rowDate: { fontSize: 11, fontWeight: "600", marginTop: 4 },
  rowCheck: { fontSize: 16 },
  rowLock: { fontSize: 16 },
});
