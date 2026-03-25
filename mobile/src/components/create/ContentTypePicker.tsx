/**
 * LAYERS - Content Type Picker
 * ====================================
 * Beautiful horizontal carousel for choosing artifact type.
 * Each type has an emoji, label, and description.
 * Selected type glows with accent color.
 *
 * Available types for manual creation:
 *   ✉️ LETTER   — Text message/memory
 *   🎤 VOICE    — Voice note (placeholder for Day 5+)
 *   📸 PHOTO    — Photo memory (placeholder for Day 5+)
 *   📓 NOTEBOOK — Shared writing spot
 *
 * Special types (created via dedicated flows):
 *   ✈️ PAPER_PLANE  — Random flight (Week 5)
 *   ⏰ TIME_CAPSULE — Future unlock (Week 5)
 *   🎁 VOUCHER      — Business rewards (Week 7)
 */

import React, { memo } from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  Platform,
} from "react-native";

// ============================================================
// TYPES
// ============================================================

export type CreatableContentType = "LETTER" | "VOICE" | "PHOTO" | "NOTEBOOK";

interface ContentTypeOption {
  type: CreatableContentType;
  emoji: string;
  shadowEmoji: string;
  label: string;
  description: string;
  available: boolean; // false = "Coming soon"
}

interface Props {
  selected: CreatableContentType;
  onSelect: (type: CreatableContentType) => void;
  isShadow: boolean;
}

// ============================================================
// OPTIONS CONFIG
// ============================================================

const CONTENT_TYPES: ContentTypeOption[] = [
  {
    type: "LETTER",
    emoji: "✉️",
    shadowEmoji: "💀",
    label: "Letter",
    description: "Write a message or memory",
    available: true,
  },
  {
    type: "PHOTO",
    emoji: "📸",
    shadowEmoji: "👁️",
    label: "Photo",
    description: "Drop a photo memory",
    available: false, // Week 5: file upload
  },
  {
    type: "VOICE",
    emoji: "🎤",
    shadowEmoji: "👻",
    label: "Voice",
    description: "Record a voice note",
    available: false, // Week 5: audio recording
  },
  {
    type: "NOTEBOOK",
    emoji: "📓",
    shadowEmoji: "📜",
    label: "Notebook",
    description: "Collaborative writing spot",
    available: true,
  },
];

// ============================================================
// COMPONENT
// ============================================================

function ContentTypePickerComponent({ selected, onSelect, isShadow }: Props) {
  const accentColor = isShadow ? "#8B5CF6" : "#3B82F6";

  return (
    <View style={styles.container}>
      <Text
        style={[
          styles.sectionLabel,
          { color: isShadow ? "#A78BFA" : "#6B7280" },
        ]}
      >
        What are you dropping?
      </Text>

      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.scrollContent}
      >
        {CONTENT_TYPES.map((option) => {
          const isSelected = selected === option.type;
          const emoji = isShadow ? option.shadowEmoji : option.emoji;

          return (
            <TouchableOpacity
              key={option.type}
              style={[
                styles.typeCard,
                {
                  backgroundColor: isSelected
                    ? isShadow
                      ? "rgba(139, 92, 246, 0.15)"
                      : "rgba(59, 130, 246, 0.1)"
                    : isShadow
                      ? "rgba(255, 255, 255, 0.05)"
                      : "rgba(0, 0, 0, 0.03)",
                  borderColor: isSelected ? accentColor : "transparent",
                  opacity: option.available ? 1 : 0.5,
                },
              ]}
              onPress={() => {
                if (option.available) onSelect(option.type);
              }}
              activeOpacity={option.available ? 0.7 : 1}
            >
              <Text style={styles.typeEmoji}>{emoji}</Text>
              <Text
                style={[
                  styles.typeLabel,
                  {
                    color: isSelected
                      ? accentColor
                      : isShadow
                        ? "#E5E7EB"
                        : "#374151",
                  },
                ]}
              >
                {option.label}
              </Text>
              {!option.available && <Text style={styles.comingSoon}>Soon</Text>}
            </TouchableOpacity>
          );
        })}
      </ScrollView>
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
  scrollContent: {
    gap: 10,
    paddingHorizontal: 2,
  },
  typeCard: {
    width: 80,
    paddingVertical: 12,
    paddingHorizontal: 8,
    borderRadius: 14,
    alignItems: "center",
    borderWidth: 1.5,
  },
  typeEmoji: {
    fontSize: 28,
    marginBottom: 6,
  },
  typeLabel: {
    fontSize: 12,
    fontWeight: "600",
    textAlign: "center",
  },
  comingSoon: {
    fontSize: 9,
    color: "#9CA3AF",
    marginTop: 2,
    fontStyle: "italic",
  },
});

export default memo(ContentTypePickerComponent);
