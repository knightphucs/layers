/**
 * LAYERS - Privacy Selector
 * ====================================
 * Choose who can see your artifact:
 *   🌍 PUBLIC    — Anyone nearby can read it
 *   🎯 TARGETED  — Sent to a specific user (Week 5: user search)
 *   🔐 PASSCODE  — Requires a secret code to unlock
 *
 * When PASSCODE is selected, a text input appears for the code.
 * When TARGETED is selected, a username input appears.
 */

import React, { memo, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  TextInput,
  Platform,
} from "react-native";

// ============================================================
// TYPES
// ============================================================

export type VisibilityMode = "PUBLIC" | "TARGETED" | "PASSCODE";

interface Props {
  selected: VisibilityMode;
  onSelect: (mode: VisibilityMode) => void;
  passcode: string;
  onPasscodeChange: (code: string) => void;
  targetUsername: string;
  onTargetUsernameChange: (username: string) => void;
  isShadow: boolean;
}

interface PrivacyOption {
  mode: VisibilityMode;
  emoji: string;
  label: string;
  desc: string;
  available: boolean;
}

const OPTIONS: PrivacyOption[] = [
  {
    mode: "PUBLIC",
    emoji: "🌍",
    label: "Public",
    desc: "Anyone nearby can find it",
    available: true,
  },
  {
    mode: "PASSCODE",
    emoji: "🔐",
    label: "Passcode",
    desc: "Share the code with friends",
    available: true,
  },
  {
    mode: "TARGETED",
    emoji: "🎯",
    label: "Targeted",
    desc: "Only one person can see it",
    available: false, // Week 5: user search
  },
];

// ============================================================
// COMPONENT
// ============================================================

function PrivacySelectorComponent({
  selected,
  onSelect,
  passcode,
  onPasscodeChange,
  targetUsername,
  onTargetUsernameChange,
  isShadow,
}: Props) {
  const accentColor = isShadow ? "#8B5CF6" : "#3B82F6";
  const surfaceColor = isShadow ? "rgba(255,255,255,0.05)" : "rgba(0,0,0,0.03)";
  const textColor = isShadow ? "#E5E7EB" : "#374151";
  const subtextColor = isShadow ? "#9CA3AF" : "#6B7280";
  const inputBg = isShadow ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.05)";

  return (
    <View style={styles.container}>
      <Text style={[styles.sectionLabel, { color: subtextColor }]}>
        Who can see this?
      </Text>

      <View style={styles.optionsRow}>
        {OPTIONS.map((option) => {
          const isSelected = selected === option.mode;
          return (
            <TouchableOpacity
              key={option.mode}
              style={[
                styles.optionCard,
                {
                  backgroundColor: isSelected
                    ? isShadow
                      ? "rgba(139, 92, 246, 0.15)"
                      : "rgba(59, 130, 246, 0.1)"
                    : surfaceColor,
                  borderColor: isSelected ? accentColor : "transparent",
                  opacity: option.available ? 1 : 0.45,
                },
              ]}
              onPress={() => {
                if (option.available) onSelect(option.mode);
              }}
              activeOpacity={option.available ? 0.7 : 1}
            >
              <Text style={styles.optionEmoji}>{option.emoji}</Text>
              <Text
                style={[
                  styles.optionLabel,
                  { color: isSelected ? accentColor : textColor },
                ]}
              >
                {option.label}
              </Text>
              <Text style={[styles.optionDesc, { color: subtextColor }]}>
                {option.available ? option.desc : "Coming soon"}
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>

      {/* Passcode input */}
      {selected === "PASSCODE" && (
        <View style={styles.inputRow}>
          <Text style={[styles.inputLabel, { color: subtextColor }]}>
            🔑 Set a passcode:
          </Text>
          <TextInput
            style={[
              styles.textInput,
              {
                backgroundColor: inputBg,
                color: textColor,
                borderColor: accentColor + "40",
              },
            ]}
            value={passcode}
            onChangeText={onPasscodeChange}
            placeholder="e.g. mysecret123"
            placeholderTextColor={subtextColor}
            maxLength={32}
            autoCapitalize="none"
            autoCorrect={false}
          />
          <Text style={[styles.inputHint, { color: subtextColor }]}>
            Share this code with whoever you want to read it
          </Text>
        </View>
      )}

      {/* Target username input (placeholder for Week 5) */}
      {selected === "TARGETED" && (
        <View style={styles.inputRow}>
          <Text style={[styles.inputLabel, { color: subtextColor }]}>
            🎯 Send to user:
          </Text>
          <TextInput
            style={[
              styles.textInput,
              {
                backgroundColor: inputBg,
                color: textColor,
                borderColor: accentColor + "40",
              },
            ]}
            value={targetUsername}
            onChangeText={onTargetUsernameChange}
            placeholder="@username"
            placeholderTextColor={subtextColor}
            maxLength={30}
            autoCapitalize="none"
            autoCorrect={false}
          />
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginBottom: 16,
  },
  sectionLabel: {
    fontSize: 13,
    fontWeight: "600",
    marginBottom: 10,
    paddingHorizontal: 4,
  },
  optionsRow: {
    flexDirection: "row",
    gap: 10,
  },
  optionCard: {
    flex: 1,
    paddingVertical: 12,
    paddingHorizontal: 8,
    borderRadius: 14,
    alignItems: "center",
    borderWidth: 1.5,
  },
  optionEmoji: {
    fontSize: 22,
    marginBottom: 4,
  },
  optionLabel: {
    fontSize: 13,
    fontWeight: "700",
    marginBottom: 2,
  },
  optionDesc: {
    fontSize: 10,
    textAlign: "center",
    lineHeight: 13,
  },
  inputRow: {
    marginTop: 12,
    paddingHorizontal: 4,
  },
  inputLabel: {
    fontSize: 13,
    fontWeight: "600",
    marginBottom: 6,
  },
  textInput: {
    borderWidth: 1,
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: Platform.OS === "ios" ? 12 : 10,
    fontSize: 15,
  },
  inputHint: {
    fontSize: 11,
    marginTop: 4,
    paddingHorizontal: 2,
  },
});

export default memo(PrivacySelectorComponent);
