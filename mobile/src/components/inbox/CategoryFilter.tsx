/**
 * LAYERS — CategoryFilter Component
 * ==========================================
 * Horizontal scrollable filter pills for inbox categories.
 *
 * Categories:
 *   All | Letters | Replies | Paper Planes | Time Capsules
 *
 * PATTERN: React.memo, same as other Week 4 components.
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
import { InboxCategory } from "../../types/inbox";

// ============================================================
// CATEGORY CONFIG
// ============================================================

const CATEGORIES: {
  key: InboxCategory | "all";
  label: string;
  icon: string;
}[] = [
  { key: "all", label: "All", icon: "📬" },
  { key: "received", label: "Letters", icon: "✉️" },
  { key: "replies", label: "Replies", icon: "💬" },
  { key: "paper_planes", label: "Planes", icon: "✈️" },
  { key: "time_capsules", label: "Capsules", icon: "⏰" },
];

// ============================================================
// COMPONENT
// ============================================================

interface CategoryFilterProps {
  selected: InboxCategory | "all";
  onSelect: (category: InboxCategory | "all") => void;
  unreadCounts?: Record<string, number>;
}

const CategoryFilter = React.memo(
  ({ selected, onSelect, unreadCounts }: CategoryFilterProps) => {
    const layer = useAuthStore((s) => s.layer);
    const colors = Colors[layer.toLowerCase() as "light" | "shadow"];

    return (
      <View style={styles.container}>
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.scrollContent}
        >
          {CATEGORIES.map((cat) => {
            const isActive = selected === cat.key;
            const count = unreadCounts?.[cat.key] || 0;

            return (
              <TouchableOpacity
                key={cat.key}
                onPress={() => onSelect(cat.key)}
                activeOpacity={0.7}
                style={[
                  styles.pill,
                  {
                    backgroundColor: isActive ? colors.primary : colors.surface,
                    borderColor: isActive ? colors.primary : colors.border,
                  },
                ]}
              >
                <Text style={styles.pillIcon}>{cat.icon}</Text>
                <Text
                  style={[
                    styles.pillLabel,
                    {
                      color: isActive ? "#FFFFFF" : colors.text,
                      fontWeight: isActive ? "600" : "400",
                    },
                  ]}
                >
                  {cat.label}
                </Text>
                {count > 0 && (
                  <View
                    style={[
                      styles.badge,
                      {
                        backgroundColor: isActive
                          ? "#FFFFFF30"
                          : colors.primary,
                      },
                    ]}
                  >
                    <Text
                      style={[
                        styles.badgeText,
                        {
                          color: isActive ? "#FFFFFF" : "#FFFFFF",
                        },
                      ]}
                    >
                      {count > 99 ? "99+" : count}
                    </Text>
                  </View>
                )}
              </TouchableOpacity>
            );
          })}
        </ScrollView>
      </View>
    );
  },
);

CategoryFilter.displayName = "CategoryFilter";

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
  badge: {
    minWidth: 18,
    height: 18,
    borderRadius: 9,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 5,
    marginLeft: 2,
  },
  badgeText: {
    fontSize: 10,
    fontWeight: "700",
  },
});

export default CategoryFilter;
