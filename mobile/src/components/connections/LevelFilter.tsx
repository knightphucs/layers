/**
 * LAYERS — LevelFilter Component
 * ==========================================
 * Horizontal scrollable filter pills for connection levels.
 *
 * Filters:
 *   All | Strangers | Signals | Connected
 */

import React, { useCallback } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  ScrollView,
  StyleSheet,
} from "react-native";
import { Colors } from "../../constants/colors";
import { useAuthStore } from "../../store/authStore";
import { ConnectionLevel } from "../../types/connections";

// ============================================================
// FILTER CONFIG
// ============================================================

interface FilterItem {
  key: "all" | ConnectionLevel;
  label: string;
  icon: string;
}

const FILTERS: FilterItem[] = [
  { key: "all", label: "All", icon: "📬" },
  { key: "STRANGER", label: "Strangers", icon: "👤" },
  { key: "SIGNAL", label: "Signals", icon: "📡" },
  { key: "CONNECTED", label: "Connected", icon: "✨" },
];

// ============================================================
// COMPONENT
// ============================================================

interface LevelFilterProps {
  selected: ConnectionLevel | "all";
  onSelect: (filter: ConnectionLevel | "all") => void;
  counts: {
    all: number;
    STRANGER: number;
    SIGNAL: number;
    CONNECTED: number;
  };
}

const LevelFilter = React.memo(
  ({ selected, onSelect, counts }: LevelFilterProps) => {
    const layer = useAuthStore((s) => s.layer);
    const colors = Colors[layer.toLowerCase() as "light" | "shadow"];

    return (
      <View style={styles.container}>
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.scrollContent}
        >
          {FILTERS.map((f) => {
            const isActive = selected === f.key;
            const count = counts[f.key as keyof typeof counts];

            return (
              <TouchableOpacity
                key={f.key}
                onPress={() => onSelect(f.key)}
                activeOpacity={0.7}
                style={[
                  styles.pill,
                  {
                    backgroundColor: isActive ? colors.primary : colors.surface,
                    borderColor: isActive ? colors.primary : colors.border,
                  },
                ]}
              >
                <Text style={styles.pillIcon}>{f.icon}</Text>
                <Text
                  style={[
                    styles.pillLabel,
                    {
                      color: isActive ? "#FFFFFF" : colors.text,
                      fontWeight: isActive ? "600" : "400",
                    },
                  ]}
                >
                  {f.label}
                </Text>
                <Text
                  style={[
                    styles.pillCount,
                    {
                      color: isActive ? "#FFFFFF" : colors.textSecondary,
                    },
                  ]}
                >
                  {count}
                </Text>
              </TouchableOpacity>
            );
          })}
        </ScrollView>
      </View>
    );
  },
);

LevelFilter.displayName = "LevelFilter";

// ============================================================
// STYLES
// ============================================================

const styles = StyleSheet.create({
  container: {
    paddingVertical: 10,
  },
  scrollContent: {
    paddingHorizontal: 16,
    gap: 8,
  },
  pill: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 20,
    borderWidth: 1,
    gap: 5,
  },
  pillIcon: {
    fontSize: 14,
  },
  pillLabel: {
    fontSize: 13,
  },
  pillCount: {
    fontSize: 12,
    fontWeight: "600",
    marginLeft: 2,
  },
});

export default LevelFilter;
