/**
 * LAYERS — CampfireHeader Component
 * ==================================================
 * Top header for the CampfireScreen. Replaces ChatHeader for campfires.
 *
 * Shows:
 *   - Campfire name (or "Campfire" fallback)
 *   - "X here" member count
 *   - Live countdown to expiry (updates every minute via setInterval)
 *   - Back button + prominent "Leave fire 🔥" button
 */

import React, { useState, useEffect, useCallback } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Platform,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Colors } from "../../constants/colors";
import { useAuthStore } from "../../store/authStore";

// ============================================================
// HELPERS
// ============================================================

/**
 * Format the time remaining until `expiresAt`.
 *   > 1h   → "1h 23m left"
 *   < 1h   → "45m left"
 *   < 1m   → "Expiring…"
 *   past   → "Expired"
 */
function formatCountdown(expiresAt: string | null): string {
  if (!expiresAt) return "";
  const now = Date.now();
  const exp = new Date(expiresAt).getTime();
  const diffMs = exp - now;

  if (diffMs <= 0) return "Expired";
  const totalMin = Math.floor(diffMs / 60_000);
  if (totalMin < 1) return "Expiring…";
  const hours = Math.floor(totalMin / 60);
  const mins = totalMin % 60;
  if (hours > 0) return `${hours}h ${mins}m left`;
  return `${mins}m left`;
}

// ============================================================
// COMPONENT
// ============================================================

interface CampfireHeaderProps {
  name: string | null;
  expiresAt: string | null;
  memberCount: number;
  onlineCount: number;
  onBack: () => void;
  onLeave: () => void;
}

export function CampfireHeader({
  name,
  expiresAt,
  memberCount,
  onlineCount,
  onBack,
  onLeave,
}: CampfireHeaderProps) {
  const layer = useAuthStore((s) => s.layer);
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];

  // Live countdown — re-render every 60s
  const [countdown, setCountdown] = useState(() => formatCountdown(expiresAt));

  useEffect(() => {
    setCountdown(formatCountdown(expiresAt));
    const interval = setInterval(() => {
      setCountdown(formatCountdown(expiresAt));
    }, 60_000);
    return () => clearInterval(interval);
  }, [expiresAt]);

  const isExpiring = countdown === "Expiring…" || countdown === "Expired";

  const displayName = name || "Campfire";
  const presenceLabel =
    onlineCount > 0
      ? `${onlineCount} here now`
      : `${memberCount} ${memberCount === 1 ? "member" : "members"}`;

  return (
    <SafeAreaView
      edges={["top"]}
      style={[
        styles.safe,
        { backgroundColor: colors.surface, borderBottomColor: colors.border },
      ]}
    >
      <View style={styles.row}>
        <TouchableOpacity
          onPress={onBack}
          style={styles.backBtn}
          activeOpacity={0.7}
          hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
        >
          <Text style={[styles.backIcon, { color: colors.text }]}>‹</Text>
        </TouchableOpacity>

        <View style={styles.titleCol}>
          <View style={styles.titleRow}>
            <Text style={styles.fireIcon}>🔥</Text>
            <Text
              style={[styles.name, { color: colors.text }]}
              numberOfLines={1}
            >
              {displayName}
            </Text>
          </View>
          <View style={styles.metaRow}>
            <Text style={[styles.presence, { color: colors.textSecondary }]}>
              {presenceLabel}
            </Text>
            {countdown !== "" && (
              <>
                <Text style={[styles.dot, { color: colors.textSecondary }]}>
                  ·
                </Text>
                <Text
                  style={[
                    styles.countdown,
                    {
                      color: isExpiring ? "#EF4444" : colors.textSecondary,
                    },
                  ]}
                >
                  {countdown}
                </Text>
              </>
            )}
          </View>
        </View>

        <TouchableOpacity
          onPress={onLeave}
          style={[styles.leaveBtn, { backgroundColor: "#EF4444" + "15" }]}
          activeOpacity={0.7}
        >
          <Text style={styles.leaveText}>Leave 🔥</Text>
        </TouchableOpacity>
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: {
    borderBottomWidth: 1,
  },
  row: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 6,
    paddingVertical: Platform.OS === "ios" ? 8 : 12,
  },
  backBtn: {
    width: 34,
    height: 34,
    alignItems: "center",
    justifyContent: "center",
  },
  backIcon: {
    fontSize: 32,
    fontWeight: "300",
    marginTop: -4,
  },
  titleCol: {
    flex: 1,
    marginHorizontal: 4,
  },
  titleRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  fireIcon: {
    fontSize: 15,
  },
  name: {
    flex: 1,
    fontSize: 16,
    fontWeight: "600",
  },
  metaRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 5,
    marginTop: 2,
  },
  presence: {
    fontSize: 12,
  },
  dot: {
    fontSize: 12,
  },
  countdown: {
    fontSize: 12,
    fontWeight: "500",
  },
  leaveBtn: {
    paddingHorizontal: 12,
    paddingVertical: 7,
    borderRadius: 16,
  },
  leaveText: {
    color: "#EF4444",
    fontSize: 13,
    fontWeight: "600",
  },
});

export default CampfireHeader;
