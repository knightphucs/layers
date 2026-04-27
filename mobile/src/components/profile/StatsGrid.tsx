/**
 * LAYERS — StatsGrid Component
 * ==========================================
 * Visual stats dashboard for the profile screen.
 *
 * Sections:
 *   1. XP Progress Bar (level progress + XP to next level)
 *   2. Exploration Stats (chunks, area, % of city)
 *   3. Content Stats (artifacts, replies, planes)
 *
 * PATTERN: React.memo.
 */

import React from "react";
import { View, Text, StyleSheet } from "react-native";
import { Colors } from "../../constants/colors";
import { useAuthStore } from "../../store/authStore";
import { ProfileStats } from "../../services/profile";

interface StatsGridProps {
  stats: ProfileStats;
}

const StatsGrid = React.memo(({ stats }: StatsGridProps) => {
  const layer = useAuthStore((s) => s.layer);
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];

  return (
    <View style={styles.container}>
      {/* XP Progress */}
      <View
        style={[
          styles.xpCard,
          { backgroundColor: colors.surface, borderColor: colors.border },
        ]}
      >
        <View style={styles.xpHeader}>
          <Text style={[styles.xpLabel, { color: colors.text }]}>
            ⭐ Experience Points
          </Text>
          <Text style={[styles.xpValue, { color: colors.primary }]}>
            {stats.xp.toLocaleString()} XP
          </Text>
        </View>
        {/* Progress bar */}
        <View
          style={[
            styles.progressTrack,
            { backgroundColor: colors.border + "50" },
          ]}
        >
          <View
            style={[
              styles.progressFill,
              {
                backgroundColor: colors.primary,
                width: `${Math.min(100, stats.level_progress * 100)}%`,
              },
            ]}
          />
        </View>
        <Text style={[styles.xpRemaining, { color: colors.textSecondary }]}>
          {stats.xp_to_next_level.toLocaleString()} XP to Level{" "}
          {stats.level + 1}
        </Text>
      </View>

      {/* Exploration Stats */}
      <Text style={[styles.sectionTitle, { color: colors.textSecondary }]}>
        EXPLORATION
      </Text>
      <View style={styles.grid}>
        <StatCard
          icon="🗺️"
          value={stats.chunks_explored.toString()}
          label="Areas explored"
          colors={colors}
        />
        <StatCard
          icon="📐"
          value={`${stats.area_explored_km2}km²`}
          label="Area covered"
          colors={colors}
        />
        <StatCard
          icon="🌆"
          value={`${stats.city_percentage}%`}
          label="City explored"
          colors={colors}
        />
        <StatCard
          icon="📅"
          value={stats.days_active.toString()}
          label="Days active"
          colors={colors}
        />
      </View>

      {/* Content Stats */}
      <Text style={[styles.sectionTitle, { color: colors.textSecondary }]}>
        MEMORIES
      </Text>
      <View style={styles.grid}>
        <StatCard
          icon="✉️"
          value={stats.artifacts_created.toString()}
          label="Created"
          colors={colors}
        />
        <StatCard
          icon="💬"
          value={stats.replies_received.toString()}
          label="Replies"
          colors={colors}
        />
        <StatCard
          icon="✈️"
          value={stats.paper_planes_thrown.toString()}
          label="Planes thrown"
          colors={colors}
        />
        <StatCard
          icon="💎"
          value={stats.reputation.toString()}
          label="Reputation"
          colors={colors}
        />
      </View>
    </View>
  );
});

StatsGrid.displayName = "StatsGrid";

// ============================================================
// SINGLE STAT CARD
// ============================================================

interface StatCardProps {
  icon: string;
  value: string;
  label: string;
  colors: any;
}

function StatCard({ icon, value, label, colors }: StatCardProps) {
  return (
    <View
      style={[
        styles.statCard,
        { backgroundColor: colors.surface, borderColor: colors.border },
      ]}
    >
      <Text style={styles.statIcon}>{icon}</Text>
      <Text style={[styles.statValue, { color: colors.text }]}>{value}</Text>
      <Text style={[styles.statLabel, { color: colors.textSecondary }]}>
        {label}
      </Text>
    </View>
  );
}

// ============================================================
// STYLES
// ============================================================

const styles = StyleSheet.create({
  container: {
    paddingHorizontal: 16,
  },
  xpCard: {
    borderRadius: 14,
    borderWidth: 1,
    padding: 16,
    marginBottom: 20,
  },
  xpHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 10,
  },
  xpLabel: {
    fontSize: 14,
    fontWeight: "600",
  },
  xpValue: {
    fontSize: 16,
    fontWeight: "700",
  },
  progressTrack: {
    height: 8,
    borderRadius: 4,
    overflow: "hidden",
    marginBottom: 6,
  },
  progressFill: {
    height: "100%",
    borderRadius: 4,
  },
  xpRemaining: {
    fontSize: 12,
    textAlign: "right",
  },
  sectionTitle: {
    fontSize: 12,
    fontWeight: "600",
    letterSpacing: 0.5,
    marginBottom: 10,
    marginTop: 4,
  },
  grid: {
    flexDirection: "row",
    flexWrap: "wrap",
    gap: 10,
    marginBottom: 16,
  },
  statCard: {
    width: "47%",
    flexGrow: 1,
    borderRadius: 12,
    borderWidth: 1,
    padding: 14,
    alignItems: "center",
  },
  statIcon: {
    fontSize: 22,
    marginBottom: 6,
  },
  statValue: {
    fontSize: 20,
    fontWeight: "700",
    marginBottom: 2,
  },
  statLabel: {
    fontSize: 12,
  },
});

export default StatsGrid;
