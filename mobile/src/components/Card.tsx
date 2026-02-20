// ===========================================
// Consistent card styling across the app
// ===========================================

import React from "react";
import { View, StyleSheet, ViewStyle, TouchableOpacity } from "react-native";
import { Colors } from "../constants/colors";
import { useAuthStore } from "../store/authStore";

interface CardProps {
  children: React.ReactNode;
  style?: ViewStyle;
  onPress?: () => void;
  variant?: "default" | "elevated" | "outlined";
  padding?: "none" | "small" | "medium" | "large";
}

export default function Card({
  children,
  style,
  onPress,
  variant = "default",
  padding = "medium",
}: CardProps) {
  const layer = useAuthStore((state) => state.layer);
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];

  const getVariantStyle = (): ViewStyle => {
    switch (variant) {
      case "elevated":
        return {
          backgroundColor: colors.surface,
          shadowColor: "#000",
          shadowOffset: { width: 0, height: 4 },
          shadowOpacity: 0.15,
          shadowRadius: 12,
          elevation: 8,
        };
      case "outlined":
        return {
          backgroundColor: "transparent",
          borderWidth: 1,
          borderColor: colors.border,
        };
      default:
        return {
          backgroundColor: colors.surface,
          shadowColor: "#000",
          shadowOffset: { width: 0, height: 2 },
          shadowOpacity: 0.05,
          shadowRadius: 8,
          elevation: 2,
        };
    }
  };

  const getPaddingStyle = (): ViewStyle => {
    switch (padding) {
      case "none":
        return { padding: 0 };
      case "small":
        return { padding: 12 };
      case "large":
        return { padding: 24 };
      default:
        return { padding: 16 };
    }
  };

  const cardStyle = [styles.card, getVariantStyle(), getPaddingStyle(), style];

  if (onPress) {
    return (
      <TouchableOpacity style={cardStyle} onPress={onPress} activeOpacity={0.7}>
        {children}
      </TouchableOpacity>
    );
  }

  return <View style={cardStyle}>{children}</View>;
}

const styles = StyleSheet.create({
  card: {
    borderRadius: 16,
    overflow: "hidden",
  },
});
