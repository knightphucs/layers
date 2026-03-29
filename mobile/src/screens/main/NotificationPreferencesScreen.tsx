/**
 * LAYERS — NotificationPreferencesScreen
 * ==========================================
 * Settings screen for notification preferences.
 *
 * Sections:
 *   1. Master toggle (enable/disable all)
 *   2. Category toggles (social, discovery, inbox, capsule, system)
 *   3. Quiet hours (start/end time)
 *
 * NAVIGATION:
 *   Accessed from Profile screen → Settings → Notifications
 *   For MVP: Can be opened from a button on ProfileScreen.
 */

import React, { useEffect, useCallback } from "react";
import {
  View,
  Text,
  Switch,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  Alert,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useAuthStore } from "../../store/authStore";
import { useNotificationStore } from "../../store/notificationStore";
import { Colors } from "../../constants/colors";
import { NotificationCategory } from "../../types/notifications";

// ============================================================
// CATEGORY CONFIG
// ============================================================

const CATEGORIES: {
  key: NotificationCategory;
  label: string;
  icon: string;
  description: string;
}[] = [
  {
    key: "social",
    label: "Social",
    icon: "💬",
    description: "Replies to your letters, connection requests",
  },
  {
    key: "discovery",
    label: "Discovery",
    icon: "📍",
    description: "Artifacts nearby, new content in your area",
  },
  {
    key: "inbox",
    label: "Inbox",
    icon: "✉️",
    description: "Slow Mail delivered, Paper Planes landed",
  },
  {
    key: "capsule",
    label: "Time Capsules",
    icon: "⏰",
    description: "Capsule opened, unlock reminders",
  },
  {
    key: "system",
    label: "System",
    icon: "🎮",
    description: "Level ups, badges, daily missions",
  },
];

// ============================================================
// COMPONENT
// ============================================================

interface Props {
  onBack?: () => void;
}

export default function NotificationPreferencesScreen({ onBack }: Props) {
  const layer = useAuthStore((s) => s.layer);
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];

  const {
    preferences,
    isLoading,
    loadPreferences,
    toggleCategory,
    toggleMasterSwitch,
    updatePreference,
    savePreferences,
  } = useNotificationStore();

  useEffect(() => {
    loadPreferences();
  }, []);

  const handleQuietHoursToggle = useCallback(() => {
    updatePreference("quiet_hours_enabled", !preferences.quiet_hours_enabled);
    // Debounced save
    setTimeout(() => savePreferences(), 500);
  }, [preferences.quiet_hours_enabled, updatePreference, savePreferences]);

  const handleQuietHoursEdit = useCallback(() => {
    Alert.alert(
      "Quiet Hours",
      `Current: ${preferences.quiet_hours_start} - ${preferences.quiet_hours_end}\n\nDuring quiet hours, notifications are silenced.`,
      [
        {
          text: "Set to 23:00 - 07:00",
          onPress: () => {
            updatePreference("quiet_hours_start", "23:00");
            updatePreference("quiet_hours_end", "07:00");
            savePreferences();
          },
        },
        {
          text: "Set to 22:00 - 08:00",
          onPress: () => {
            updatePreference("quiet_hours_start", "22:00");
            updatePreference("quiet_hours_end", "08:00");
            savePreferences();
          },
        },
        { text: "Cancel", style: "cancel" },
      ],
    );
  }, [preferences, updatePreference, savePreferences]);

  // ========================================================
  // RENDER
  // ========================================================

  return (
    <SafeAreaView
      style={[styles.container, { backgroundColor: colors.background }]}
      edges={["top"]}
    >
      {/* Header */}
      <View style={styles.header}>
        {onBack && (
          <TouchableOpacity onPress={onBack} style={styles.backButton}>
            <Text style={[styles.backText, { color: colors.primary }]}>
              ← Back
            </Text>
          </TouchableOpacity>
        )}
        <Text style={[styles.headerTitle, { color: colors.text }]}>
          Notifications
        </Text>
      </View>

      <ScrollView
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        {/* Master Toggle */}
        <View
          style={[
            styles.section,
            { backgroundColor: colors.surface, borderColor: colors.border },
          ]}
        >
          <View style={styles.row}>
            <View style={styles.rowLeft}>
              <Text style={styles.rowIcon}>🔔</Text>
              <View>
                <Text style={[styles.rowLabel, { color: colors.text }]}>
                  Push Notifications
                </Text>
                <Text
                  style={[
                    styles.rowDescription,
                    { color: colors.textSecondary },
                  ]}
                >
                  {preferences.enabled ? "Enabled" : "All notifications off"}
                </Text>
              </View>
            </View>
            <Switch
              value={preferences.enabled}
              onValueChange={toggleMasterSwitch}
              trackColor={{ false: colors.border, true: colors.primary + "80" }}
              thumbColor={preferences.enabled ? colors.primary : "#f4f3f4"}
            />
          </View>
        </View>

        {/* Categories */}
        <Text style={[styles.sectionTitle, { color: colors.textSecondary }]}>
          NOTIFICATION TYPES
        </Text>
        <View
          style={[
            styles.section,
            { backgroundColor: colors.surface, borderColor: colors.border },
          ]}
        >
          {CATEGORIES.map((cat, index) => (
            <View key={cat.key}>
              <View style={styles.row}>
                <View style={styles.rowLeft}>
                  <Text style={styles.rowIcon}>{cat.icon}</Text>
                  <View style={styles.rowTextContainer}>
                    <Text
                      style={[
                        styles.rowLabel,
                        {
                          color: preferences.enabled
                            ? colors.text
                            : colors.textSecondary,
                        },
                      ]}
                    >
                      {cat.label}
                    </Text>
                    <Text
                      style={[
                        styles.rowDescription,
                        { color: colors.textSecondary },
                      ]}
                    >
                      {cat.description}
                    </Text>
                  </View>
                </View>
                <Switch
                  value={preferences.enabled && preferences[cat.key]}
                  onValueChange={() => toggleCategory(cat.key)}
                  disabled={!preferences.enabled}
                  trackColor={{
                    false: colors.border,
                    true: colors.primary + "80",
                  }}
                  thumbColor={
                    preferences.enabled && preferences[cat.key]
                      ? colors.primary
                      : "#f4f3f4"
                  }
                />
              </View>
              {index < CATEGORIES.length - 1 && (
                <View
                  style={[styles.divider, { backgroundColor: colors.border }]}
                />
              )}
            </View>
          ))}
        </View>

        {/* Quiet Hours */}
        <Text style={[styles.sectionTitle, { color: colors.textSecondary }]}>
          QUIET HOURS
        </Text>
        <View
          style={[
            styles.section,
            { backgroundColor: colors.surface, borderColor: colors.border },
          ]}
        >
          <View style={styles.row}>
            <View style={styles.rowLeft}>
              <Text style={styles.rowIcon}>🌙</Text>
              <View>
                <Text style={[styles.rowLabel, { color: colors.text }]}>
                  Quiet Hours
                </Text>
                <Text
                  style={[
                    styles.rowDescription,
                    { color: colors.textSecondary },
                  ]}
                >
                  Silence notifications at night
                </Text>
              </View>
            </View>
            <Switch
              value={preferences.quiet_hours_enabled}
              onValueChange={handleQuietHoursToggle}
              trackColor={{ false: colors.border, true: colors.primary + "80" }}
              thumbColor={
                preferences.quiet_hours_enabled ? colors.primary : "#f4f3f4"
              }
            />
          </View>

          {preferences.quiet_hours_enabled && (
            <>
              <View
                style={[styles.divider, { backgroundColor: colors.border }]}
              />
              <TouchableOpacity
                onPress={handleQuietHoursEdit}
                style={styles.row}
              >
                <View style={styles.rowLeft}>
                  <Text style={styles.rowIcon}>🕐</Text>
                  <View>
                    <Text style={[styles.rowLabel, { color: colors.text }]}>
                      Schedule
                    </Text>
                    <Text
                      style={[
                        styles.rowDescription,
                        { color: colors.textSecondary },
                      ]}
                    >
                      {preferences.quiet_hours_start} —{" "}
                      {preferences.quiet_hours_end}
                    </Text>
                  </View>
                </View>
                <Text style={[styles.chevron, { color: colors.textSecondary }]}>
                  ›
                </Text>
              </TouchableOpacity>
            </>
          )}
        </View>

        {/* Info */}
        <Text style={[styles.infoText, { color: colors.textSecondary }]}>
          Notifications help you discover nearby artifacts, receive Slow Mail
          replies, and stay connected with other explorers. You can always
          change these settings later.
        </Text>
      </ScrollView>
    </SafeAreaView>
  );
}

// ============================================================
// STYLES
// ============================================================

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    paddingHorizontal: 16,
    paddingTop: 8,
    paddingBottom: 12,
  },
  backButton: {
    marginBottom: 8,
  },
  backText: {
    fontSize: 15,
    fontWeight: "500",
  },
  headerTitle: {
    fontSize: 28,
    fontWeight: "bold",
    letterSpacing: -0.5,
  },
  scrollContent: {
    paddingBottom: 40,
  },
  sectionTitle: {
    fontSize: 12,
    fontWeight: "600",
    letterSpacing: 0.5,
    marginHorizontal: 16,
    marginTop: 24,
    marginBottom: 8,
  },
  section: {
    marginHorizontal: 16,
    borderRadius: 14,
    borderWidth: 1,
    overflow: "hidden",
  },
  row: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingHorizontal: 14,
    paddingVertical: 12,
    minHeight: 56,
  },
  rowLeft: {
    flexDirection: "row",
    alignItems: "center",
    flex: 1,
    marginRight: 12,
    gap: 12,
  },
  rowIcon: {
    fontSize: 22,
    width: 30,
    textAlign: "center",
  },
  rowTextContainer: {
    flex: 1,
  },
  rowLabel: {
    fontSize: 15,
    fontWeight: "500",
  },
  rowDescription: {
    fontSize: 12,
    marginTop: 2,
    lineHeight: 16,
  },
  divider: {
    height: 1,
    marginLeft: 56,
  },
  chevron: {
    fontSize: 22,
    fontWeight: "300",
  },
  infoText: {
    fontSize: 13,
    lineHeight: 18,
    marginHorizontal: 16,
    marginTop: 20,
    textAlign: "center",
  },
});
