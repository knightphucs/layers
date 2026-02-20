import React from "react";
import { View, Text, StyleSheet, ViewStyle } from "react-native";
import { Colors } from "../constants/colors";
import { useAuthStore } from "../store/authStore";

interface DividerProps {
  text?: string;
  style?: ViewStyle;
}

export default function Divider({ text, style }: DividerProps) {
  const layer = useAuthStore((state) => state.layer);
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];

  if (text) {
    return (
      <View style={[styles.container, style]}>
        <View style={[styles.line, { backgroundColor: colors.border }]} />
        <Text style={[styles.text, { color: colors.textSecondary }]}>
          {text}
        </Text>
        <View style={[styles.line, { backgroundColor: colors.border }]} />
      </View>
    );
  }

  return (
    <View
      style={[styles.simpleLine, { backgroundColor: colors.border }, style]}
    />
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: "row",
    alignItems: "center",
    marginVertical: 24,
  },
  line: {
    flex: 1,
    height: 1,
  },
  text: {
    marginHorizontal: 16,
    fontSize: 14,
  },
  simpleLine: {
    height: 1,
    marginVertical: 16,
  },
});
