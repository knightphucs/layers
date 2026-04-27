/**
 * LAYERS — TimeCapsuleScreen (Week 5 Day 5)
 * ==========================================
 * Two-tab screen:
 *   1. CREATE — Compose + pick duration + seal
 *   2. MY CAPSULES — List of sealed/ready capsules with live countdowns
 *
 * FLOW:
 *   User taps "Time Capsule" from Profile
 *     → Opens on CREATE tab
 *     → Types message (2000 chars)
 *     → Picks preset (1w/1m/6m/1y/custom)
 *     → Taps "Seal Capsule 🔒"
 *       → API call to POST /artifacts/time-capsule
 *         → Success → switch to MY CAPSULES tab
 *           → See the new capsule with live countdown
 */

import React, { useState, useCallback, useEffect, useMemo } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
  Alert,
  ScrollView,
  FlatList,
  RefreshControl,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useAuthStore } from "../../store/authStore";
import { useLocationStore } from "../../store/locationStore";
import { Colors } from "../../constants/colors";
import { timeCapsuleService } from "../../services/planes_capsules";
import { CAPSULE_PRESETS, CapsulePreset } from "../../types/planes_capsules";
import PresetPicker from "../../components/capsules/PresetPicker";
import CapsuleCard, {
  CapsuleItem,
} from "../../components/capsules/CapsuleCard";

const MAX_LENGTH = 2000;

type Tab = "create" | "mine";

interface Props {
  onBack?: () => void;
}

export default function TimeCapsuleScreen({ onBack }: Props) {
  const layer = useAuthStore((s) => s.layer);
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];
  const currentLocation = useLocationStore((s) => s.currentLocation);

  // Tab state
  const [tab, setTab] = useState<Tab>("create");

  // Create form state
  const [text, setText] = useState("");
  const [selectedPreset, setSelectedPreset] =
    useState<CapsulePreset>("1_month");
  const [customDays, setCustomDays] = useState("30");
  const [isSealing, setIsSealing] = useState(false);

  // My capsules state
  const [myCapsules, setMyCapsules] = useState<CapsuleItem[]>([]);
  const [lockedCount, setLockedCount] = useState(0);
  const [unlockedCount, setUnlockedCount] = useState(0);
  const [isLoadingMine, setIsLoadingMine] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // ========================================================
  // COMPUTED: Unlock date from preset
  // ========================================================

  const unlockDate = useMemo(() => {
    const preset = CAPSULE_PRESETS.find((p) => p.key === selectedPreset);
    if (!preset) return null;

    let days = preset.days;
    if (preset.key === "custom") {
      days = parseInt(customDays, 10) || 30;
    }

    const date = new Date();
    date.setDate(date.getDate() + days);
    return date;
  }, [selectedPreset, customDays]);

  const formattedUnlockDate = useMemo(() => {
    if (!unlockDate) return "—";
    return unlockDate.toLocaleDateString("en-US", {
      weekday: "long",
      year: "numeric",
      month: "long",
      day: "numeric",
    });
  }, [unlockDate]);

  // Validation
  const remainingChars = MAX_LENGTH - text.length;
  const isOverLimit = remainingChars < 0;
  const customDaysNum = parseInt(customDays, 10);
  const isValidCustomDays =
    selectedPreset !== "custom" ||
    (!isNaN(customDaysNum) && customDaysNum >= 1 && customDaysNum <= 3650);
  const canSeal =
    text.trim().length > 0 && !isOverLimit && isValidCustomDays && !isSealing;

  // ========================================================
  // LOAD MY CAPSULES
  // ========================================================

  const loadMyCapsules = useCallback(async () => {
    setIsLoadingMine(true);
    try {
      const data = await timeCapsuleService.getMyCapsules();
      setMyCapsules(data.capsules);
      setLockedCount(data.locked_count);
      setUnlockedCount(data.unlocked_count);
    } catch (error) {
      console.error("Failed to load capsules:", error);
    } finally {
      setIsLoadingMine(false);
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    if (tab === "mine") {
      loadMyCapsules();
    }
  }, [tab, loadMyCapsules]);

  // ========================================================
  // SEAL CAPSULE
  // ========================================================

  const handleSeal = useCallback(async () => {
    if (!canSeal || !unlockDate) return;

    if (!currentLocation) {
      Alert.alert(
        "Location needed",
        "Capsules are anchored to a place. Turn on location to seal one here.",
        [{ text: "OK" }],
      );
      return;
    }

    Alert.alert(
      "Seal this capsule?",
      `It will unlock on:\n\n${formattedUnlockDate}\n\nYou won't be able to read it until then.`,
      [
        { text: "Cancel", style: "cancel" },
        {
          text: "Seal 🔒",
          onPress: async () => {
            setIsSealing(true);
            try {
              await timeCapsuleService.createCapsule({
                text: text.trim(),
                latitude: currentLocation.latitude,
                longitude: currentLocation.longitude,
                unlock_date: unlockDate.toISOString(),
              });

              // Clear form
              setText("");
              setSelectedPreset("1_month");
              setCustomDays("30");

              Alert.alert(
                "⏰ Capsule Sealed!",
                `Your message is locked until ${unlockDate.toLocaleDateString()}. Future you will thank present you.`,
                [
                  {
                    text: "View My Capsules",
                    onPress: () => setTab("mine"),
                  },
                ],
              );
            } catch (error: any) {
              const message =
                error?.response?.data?.detail ||
                "Failed to seal capsule. Try again.";
              Alert.alert("Couldn't seal", message);
            } finally {
              setIsSealing(false);
            }
          },
        },
      ],
    );
  }, [canSeal, unlockDate, formattedUnlockDate, currentLocation, text]);

  // ========================================================
  // OPEN CAPSULE
  // ========================================================

  const handleCapsulePress = useCallback((capsule: CapsuleItem) => {
    const isUnlocked =
      !capsule.unlock_at || new Date(capsule.unlock_at) <= new Date();

    if (!isUnlocked && capsule.unlock_at) {
      const unlockStr = new Date(capsule.unlock_at).toLocaleDateString(
        "en-US",
        {
          weekday: "long",
          year: "numeric",
          month: "long",
          day: "numeric",
        },
      );
      Alert.alert(
        "🔒 Still Sealed",
        `This capsule opens on ${unlockStr}.\n\nCome back then!`,
        [{ text: "OK" }],
      );
      return;
    }

    // Unlocked — show content
    const message = capsule.payload?.text || "(empty)";
    Alert.alert("📬 Your Past Self Wrote...", message, [
      { text: "Close", style: "cancel" },
    ]);
  }, []);

  // ========================================================
  // RENDER TAB CONTENT
  // ========================================================

  const renderCreateTab = () => (
    <ScrollView
      contentContainerStyle={styles.scroll}
      keyboardShouldPersistTaps="handled"
    >
      {/* Message input */}
      <View
        style={[
          styles.card,
          {
            backgroundColor: colors.surface,
            borderColor: isOverLimit ? "#EF4444" : colors.border,
          },
        ]}
      >
        <Text style={[styles.label, { color: colors.textSecondary }]}>
          MESSAGE TO FUTURE YOU
        </Text>
        <TextInput
          value={text}
          onChangeText={setText}
          multiline
          placeholder={
            "Dear future me,\n\nRight now I'm feeling...\nI hope that by the time you read this..."
          }
          placeholderTextColor={colors.textSecondary + "80"}
          style={[styles.input, { color: colors.text }]}
          maxLength={MAX_LENGTH + 50}
          editable={!isSealing}
        />
        <Text
          style={[
            styles.counter,
            {
              color: isOverLimit
                ? "#EF4444"
                : remainingChars < 100
                  ? "#F59E0B"
                  : colors.textSecondary,
            },
          ]}
        >
          {remainingChars} characters remaining
        </Text>
      </View>

      {/* Duration section */}
      <Text style={[styles.sectionTitle, { color: colors.textSecondary }]}>
        WHEN TO OPEN
      </Text>
      <PresetPicker selected={selectedPreset} onSelect={setSelectedPreset} />

      {/* Custom days input */}
      {selectedPreset === "custom" && (
        <View
          style={[
            styles.customBox,
            {
              backgroundColor: colors.surface,
              borderColor: isValidCustomDays ? colors.border : "#EF4444",
            },
          ]}
        >
          <Text style={[styles.customLabel, { color: colors.textSecondary }]}>
            Days from now
          </Text>
          <TextInput
            value={customDays}
            onChangeText={(v) => setCustomDays(v.replace(/[^0-9]/g, ""))}
            keyboardType="numeric"
            placeholder="30"
            placeholderTextColor={colors.textSecondary + "80"}
            style={[styles.customInput, { color: colors.text }]}
            maxLength={4}
          />
          <Text style={[styles.customRange, { color: colors.textSecondary }]}>
            1 – 3650 days
          </Text>
        </View>
      )}

      {/* Unlock date preview */}
      <View
        style={[styles.previewBox, { backgroundColor: colors.primary + "15" }]}
      >
        <Text style={[styles.previewLabel, { color: colors.primary }]}>
          📅 Unlocks on
        </Text>
        <Text style={[styles.previewDate, { color: colors.text }]}>
          {formattedUnlockDate}
        </Text>
      </View>

      {/* Info */}
      <View
        style={[
          styles.infoBox,
          { backgroundColor: colors.surface, borderColor: colors.border },
        ]}
      >
        <View style={styles.infoRow}>
          <Text style={styles.infoIcon}>📍</Text>
          <Text style={[styles.infoText, { color: colors.textSecondary }]}>
            Anchored to your current location
          </Text>
        </View>
        <View style={styles.infoRow}>
          <Text style={styles.infoIcon}>🔒</Text>
          <Text style={[styles.infoText, { color: colors.textSecondary }]}>
            You can't read it until the unlock date
          </Text>
        </View>
        <View style={styles.infoRow}>
          <Text style={styles.infoIcon}>🔔</Text>
          <Text style={[styles.infoText, { color: colors.textSecondary }]}>
            Push notification when it opens
          </Text>
        </View>
      </View>
    </ScrollView>
  );

  const renderMineTab = () => {
    if (isLoadingMine && myCapsules.length === 0) {
      return (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={colors.primary} />
        </View>
      );
    }

    if (myCapsules.length === 0) {
      return (
        <View style={styles.emptyContainer}>
          <Text style={styles.emptyIcon}>⏰</Text>
          <Text style={[styles.emptyTitle, { color: colors.text }]}>
            No capsules yet
          </Text>
          <Text style={[styles.emptyText, { color: colors.textSecondary }]}>
            Seal your first message to the future. Pick a date. Write something
            honest. See how you've changed.
          </Text>
          <TouchableOpacity
            onPress={() => setTab("create")}
            style={[styles.createCta, { backgroundColor: colors.primary }]}
          >
            <Text style={styles.createCtaText}>Create First Capsule</Text>
          </TouchableOpacity>
        </View>
      );
    }

    return (
      <FlatList
        data={myCapsules}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => (
          <CapsuleCard capsule={item} onPress={handleCapsulePress} />
        )}
        ListHeaderComponent={
          <View style={styles.statsBar}>
            <View style={styles.statItem}>
              <Text style={[styles.statNum, { color: "#F59E0B" }]}>
                {lockedCount}
              </Text>
              <Text style={[styles.statLabel, { color: colors.textSecondary }]}>
                Sealed
              </Text>
            </View>
            <View
              style={[styles.statDivider, { backgroundColor: colors.border }]}
            />
            <View style={styles.statItem}>
              <Text style={[styles.statNum, { color: "#10B981" }]}>
                {unlockedCount}
              </Text>
              <Text style={[styles.statLabel, { color: colors.textSecondary }]}>
                Ready
              </Text>
            </View>
          </View>
        }
        contentContainerStyle={{ paddingVertical: 10 }}
        refreshControl={
          <RefreshControl
            refreshing={isRefreshing}
            onRefresh={() => {
              setIsRefreshing(true);
              loadMyCapsules();
            }}
            tintColor={colors.primary}
          />
        }
      />
    );
  };

  // ========================================================
  // RENDER
  // ========================================================

  return (
    <SafeAreaView
      style={[styles.container, { backgroundColor: colors.background }]}
      edges={["top"]}
    >
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        style={{ flex: 1 }}
      >
        {/* Header */}
        <View style={styles.header}>
          {onBack && (
            <TouchableOpacity onPress={onBack} disabled={isSealing}>
              <Text style={[styles.backText, { color: colors.primary }]}>
                ← Back
              </Text>
            </TouchableOpacity>
          )}
          <Text style={[styles.title, { color: colors.text }]}>
            ⏰ Time Capsules
          </Text>
          <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
            Messages to your future self
          </Text>
        </View>

        {/* Tabs */}
        <View style={styles.tabsContainer}>
          <TouchableOpacity
            onPress={() => setTab("create")}
            style={[
              styles.tab,
              tab === "create" && { borderBottomColor: colors.primary },
            ]}
          >
            <Text
              style={[
                styles.tabText,
                {
                  color:
                    tab === "create" ? colors.primary : colors.textSecondary,
                  fontWeight: tab === "create" ? "700" : "500",
                },
              ]}
            >
              Create
            </Text>
          </TouchableOpacity>
          <TouchableOpacity
            onPress={() => setTab("mine")}
            style={[
              styles.tab,
              tab === "mine" && { borderBottomColor: colors.primary },
            ]}
          >
            <Text
              style={[
                styles.tabText,
                {
                  color: tab === "mine" ? colors.primary : colors.textSecondary,
                  fontWeight: tab === "mine" ? "700" : "500",
                },
              ]}
            >
              My Capsules ({myCapsules.length})
            </Text>
          </TouchableOpacity>
        </View>

        {/* Tab content */}
        <View style={{ flex: 1 }}>
          {tab === "create" ? renderCreateTab() : renderMineTab()}
        </View>

        {/* Seal button (only on create tab) */}
        {tab === "create" && (
          <View style={styles.footer}>
            <TouchableOpacity
              onPress={handleSeal}
              disabled={!canSeal}
              style={[
                styles.sealButton,
                {
                  backgroundColor: canSeal ? colors.primary : colors.border,
                  opacity: canSeal ? 1 : 0.6,
                },
              ]}
              activeOpacity={0.85}
            >
              {isSealing ? (
                <ActivityIndicator color="#FFFFFF" />
              ) : (
                <Text style={styles.sealButtonText}>Seal Capsule 🔒</Text>
              )}
            </TouchableOpacity>
          </View>
        )}
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

// ============================================================
// STYLES
// ============================================================

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: {
    paddingHorizontal: 16,
    paddingTop: 8,
    paddingBottom: 8,
  },
  backText: { fontSize: 15, fontWeight: "500", marginBottom: 10 },
  title: {
    fontSize: 28,
    fontWeight: "bold",
    letterSpacing: -0.5,
    marginBottom: 4,
  },
  subtitle: { fontSize: 13 },
  tabsContainer: {
    flexDirection: "row",
    paddingHorizontal: 16,
    marginTop: 8,
  },
  tab: {
    flex: 1,
    paddingVertical: 10,
    alignItems: "center",
    borderBottomWidth: 2,
    borderBottomColor: "transparent",
  },
  tabText: { fontSize: 14 },
  scroll: { padding: 16, gap: 14 },
  card: {
    borderWidth: 1,
    borderRadius: 14,
    padding: 14,
  },
  label: {
    fontSize: 11,
    fontWeight: "600",
    letterSpacing: 0.5,
    marginBottom: 8,
  },
  input: {
    fontSize: 15,
    lineHeight: 22,
    minHeight: 140,
    textAlignVertical: "top",
  },
  counter: {
    fontSize: 12,
    textAlign: "right",
    marginTop: 6,
  },
  sectionTitle: {
    fontSize: 12,
    fontWeight: "600",
    letterSpacing: 0.5,
    marginHorizontal: 16,
    marginTop: 4,
  },
  customBox: {
    borderWidth: 1,
    borderRadius: 14,
    padding: 14,
    flexDirection: "row",
    alignItems: "center",
    gap: 12,
  },
  customLabel: { fontSize: 13, flex: 1 },
  customInput: {
    fontSize: 18,
    fontWeight: "600",
    minWidth: 60,
    textAlign: "center",
  },
  customRange: { fontSize: 11 },
  previewBox: {
    padding: 14,
    borderRadius: 14,
    alignItems: "center",
  },
  previewLabel: {
    fontSize: 12,
    fontWeight: "600",
    letterSpacing: 0.5,
    marginBottom: 4,
  },
  previewDate: { fontSize: 16, fontWeight: "700" },
  infoBox: {
    borderWidth: 1,
    borderRadius: 14,
    padding: 14,
    gap: 10,
  },
  infoRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
  },
  infoIcon: { fontSize: 16, width: 24 },
  infoText: { fontSize: 13, flex: 1 },
  footer: { padding: 16, paddingTop: 8 },
  sealButton: {
    paddingVertical: 16,
    borderRadius: 14,
    alignItems: "center",
  },
  sealButtonText: {
    color: "#FFFFFF",
    fontSize: 17,
    fontWeight: "700",
  },
  statsBar: {
    flexDirection: "row",
    marginHorizontal: 16,
    marginBottom: 12,
    paddingVertical: 10,
  },
  statItem: { flex: 1, alignItems: "center" },
  statNum: { fontSize: 22, fontWeight: "700" },
  statLabel: { fontSize: 11, marginTop: 2 },
  statDivider: { width: 1, alignSelf: "center", height: 28 },
  loadingContainer: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  emptyContainer: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 40,
    paddingBottom: 80,
  },
  emptyIcon: { fontSize: 56, marginBottom: 16 },
  emptyTitle: { fontSize: 20, fontWeight: "600", marginBottom: 10 },
  emptyText: {
    fontSize: 14,
    lineHeight: 22,
    textAlign: "center",
    marginBottom: 24,
  },
  createCta: {
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 12,
  },
  createCtaText: {
    color: "#FFFFFF",
    fontSize: 14,
    fontWeight: "600",
  },
});
