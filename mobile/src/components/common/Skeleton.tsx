/**
 * LAYERS — Skeleton Loaders
 * ==========================================
 * Perceived performance > raw performance. A skeleton that mirrors the
 * final layout feels ~30% faster than a spinner showing the same wait.
 *
 * Base: <Skeleton /> — a shimmering rectangle (Animated opacity pulse,
 * useNativeDriver, zero dependencies).
 *
 * Presets (compose the base to mirror real cards):
 *   <InboxCardSkeleton />       — mirrors the inbox letter card
 *   <LeaderboardRowSkeleton />  — mirrors a leaderboard row
 *   <ProfileStatsSkeleton />    — mirrors the profile stats header
 *   <SkeletonList count={6} /Skeleton>  — helper to render N of any preset
 *
 * USAGE (InboxScreen example):
 *   {isLoading && items.length === 0 ? (
 *     <SkeletonList count={6}><InboxCardSkeleton /></SkeletonList>
 *   ) : ( <FlatList ... /> )}
 *
 * All presets are theme-aware via Colors[layer] — skeletons must not
 * flash-bang a Shadow-layer user with light grey boxes.
 */

import React, { useRef, useEffect } from "react";
import { View, Animated, StyleSheet, ViewStyle } from "react-native";
import { useAuthStore } from "../../store/authStore";
import { Colors } from "../../constants/colors";

// ============================================================
// BASE
// ============================================================

interface SkeletonProps {
  width?: number | `${number}%`;
  height?: number;
  borderRadius?: number;
  style?: ViewStyle;
}

export function Skeleton({
  width = "100%",
  height = 14,
  borderRadius = 7,
  style,
}: SkeletonProps) {
  const layer = useAuthStore((s) => s.layer);
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];

  const pulse = useRef(new Animated.Value(0.35)).current;

  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, {
          toValue: 0.7,
          duration: 700,
          useNativeDriver: true,
        }),
        Animated.timing(pulse, {
          toValue: 0.35,
          duration: 700,
          useNativeDriver: true,
        }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [pulse]);

  return (
    <Animated.View
      style={[
        {
          width,
          height,
          borderRadius,
          opacity: pulse,
          backgroundColor: colors.textSecondary,
        },
        style,
      ]}
    />
  );
}

// ============================================================
// PRESETS
// ============================================================

/** Mirrors an inbox letter card: icon + title line + preview line + meta. */
export const InboxCardSkeleton = React.memo(function InboxCardSkeleton() {
  const layer = useAuthStore((s) => s.layer);
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];

  return (
    <View
      style={[
        styles.card,
        { backgroundColor: colors.surface ?? "rgba(128,128,128,0.08)" },
      ]}
    >
      <Skeleton width={40} height={40} borderRadius={20} />
      <View style={styles.cardBody}>
        <Skeleton width="55%" height={14} />
        <Skeleton width="90%" height={11} style={styles.gapTop} />
        <Skeleton width="35%" height={10} style={styles.gapTop} />
      </View>
    </View>
  );
});

/** Mirrors a leaderboard row: rank + avatar + name + XP pill. */
export const LeaderboardRowSkeleton = React.memo(
  function LeaderboardRowSkeleton() {
    const layer = useAuthStore((s) => s.layer);
    const colors = Colors[layer.toLowerCase() as "light" | "shadow"];

    return (
      <View
        style={[
          styles.row,
          { backgroundColor: colors.surface ?? "rgba(128,128,128,0.08)" },
        ]}
      >
        <Skeleton width={24} height={16} />
        <Skeleton width={36} height={36} borderRadius={18} />
        <View style={styles.rowBody}>
          <Skeleton width="45%" height={13} />
        </View>
        <Skeleton width={64} height={22} borderRadius={11} />
      </View>
    );
  },
);

/** Mirrors the profile stats header: big avatar + name + 3 stat blocks. */
export const ProfileStatsSkeleton = React.memo(function ProfileStatsSkeleton() {
  return (
    <View style={styles.profile}>
      <Skeleton width={88} height={88} borderRadius={44} />
      <Skeleton width={140} height={18} style={styles.gapTopLg} />
      <Skeleton width={90} height={12} style={styles.gapTop} />
      <View style={styles.statsRow}>
        <Skeleton width={90} height={56} borderRadius={14} />
        <Skeleton width={90} height={56} borderRadius={14} />
        <Skeleton width={90} height={56} borderRadius={14} />
      </View>
    </View>
  );
});

// ============================================================
// LIST HELPER
// ============================================================

/** Renders `count` copies of the child skeleton. */
export function SkeletonList({
  count = 5,
  children,
}: {
  count?: number;
  children: React.ReactElement;
}) {
  return (
    <View style={styles.listWrap}>
      {Array.from({ length: count }).map((_, i) => (
        <React.Fragment key={i}>{children}</React.Fragment>
      ))}
    </View>
  );
}

// ============================================================
// STYLES
// ============================================================

const styles = StyleSheet.create({
  card: {
    flexDirection: "row",
    alignItems: "center",
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
    gap: 12,
  },
  cardBody: { flex: 1 },
  row: {
    flexDirection: "row",
    alignItems: "center",
    borderRadius: 14,
    padding: 12,
    marginBottom: 8,
    gap: 12,
  },
  rowBody: { flex: 1 },
  profile: {
    alignItems: "center",
    paddingVertical: 24,
  },
  statsRow: {
    flexDirection: "row",
    gap: 12,
    marginTop: 20,
  },
  listWrap: {
    paddingHorizontal: 16,
    paddingTop: 8,
  },
  gapTop: { marginTop: 8 },
  gapTopLg: { marginTop: 14 },
});
