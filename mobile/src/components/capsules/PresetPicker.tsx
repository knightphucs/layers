/**
 * LAYERS — PresetPicker Component (Week 5 Day 5)
 * ==========================================
 * Horizontal scrollable preset duration buttons for capsule creation.
 *
 * Presets: 1 Week | 1 Month | 6 Months | 1 Year | Custom
 */

import React from "react";
import {
  View,
  Text,
  TouchableOpacity,
  ScrollView,
  StyleSheet,
} from "react-native";
import { Colors } from "../../constants/colors";
import { useAuthStore } from "../../store/authStore";
import { CAPSULE_PRESETS, CapsulePreset } from "../../types/planes_capsules";

interface PresetPickerProps {
  selected: CapsulePreset | null;
  onSelect: (preset: CapsulePreset) => void;
}

const PresetPicker = React.memo(({ selected, onSelect }: PresetPickerProps) => {
  const layer = useAuthStore((s) => s.layer);
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];

  return (
    <View style={styles.container}>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.scroll}
      >
        {CAPSULE_PRESETS.map((preset) => {
          const isActive = selected === preset.key;
          return (
            <TouchableOpacity
              key={preset.key}
              onPress={() => onSelect(preset.key)}
              activeOpacity={0.7}
              style={[
                styles.pill,
                {
                  backgroundColor: isActive ? colors.primary : colors.surface,
                  borderColor: isActive ? colors.primary : colors.border,
                },
              ]}
            >
              <Text style={styles.icon}>{preset.icon}</Text>
              <Text
                style={[
                  styles.label,
                  {
                    color: isActive ? "#FFFFFF" : colors.text,
                    fontWeight: isActive ? "700" : "500",
                  },
                ]}
              >
                {preset.label}
              </Text>
            </TouchableOpacity>
          );
        })}
      </ScrollView>
    </View>
  );
});

PresetPicker.displayName = "PresetPicker";

const styles = StyleSheet.create({
  container: { paddingVertical: 4 },
  scroll: { paddingHorizontal: 16, gap: 8 },
  pill: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 12,
    borderWidth: 1,
    gap: 6,
  },
  icon: { fontSize: 16 },
  label: { fontSize: 14 },
});

export default PresetPicker;
