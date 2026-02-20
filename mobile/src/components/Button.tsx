// ===========================================
// Multiple variants: primary, secondary, outline, ghost
// ===========================================

import React from "react";
import {
  TouchableOpacity,
  Text,
  StyleSheet,
  ActivityIndicator,
  ViewStyle,
  TextStyle,
  View,
} from "react-native";
import { Colors } from "../constants/colors";
import { useAuthStore } from "../store/authStore";

type ButtonVariant = "primary" | "secondary" | "outline" | "ghost" | "danger";
type ButtonSize = "small" | "medium" | "large";

interface ButtonProps {
  title: string;
  onPress: () => void;
  loading?: boolean;
  disabled?: boolean;
  variant?: ButtonVariant;
  size?: ButtonSize;
  icon?: string;
  iconPosition?: "left" | "right";
  fullWidth?: boolean;
  style?: ViewStyle;
  textStyle?: TextStyle;
}

export default function Button({
  title,
  onPress,
  loading = false,
  disabled = false,
  variant = "primary",
  size = "medium",
  icon,
  iconPosition = "left",
  fullWidth = true,
  style,
  textStyle,
}: ButtonProps) {
  const layer = useAuthStore((state) => state.layer);
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];

  const getButtonStyle = (): ViewStyle => {
    const baseStyle: ViewStyle = {
      opacity: disabled || loading ? 0.6 : 1,
    };

    switch (variant) {
      case "primary":
        return { ...baseStyle, backgroundColor: colors.primary };
      case "secondary":
        return { ...baseStyle, backgroundColor: colors.secondary };
      case "outline":
        return {
          ...baseStyle,
          backgroundColor: "transparent",
          borderWidth: 2,
          borderColor: colors.primary,
        };
      case "ghost":
        return {
          ...baseStyle,
          backgroundColor: "transparent",
        };
      case "danger":
        return { ...baseStyle, backgroundColor: colors.error };
      default:
        return { ...baseStyle, backgroundColor: colors.primary };
    }
  };

  const getTextStyle = (): TextStyle => {
    switch (variant) {
      case "outline":
        return { color: colors.primary };
      case "ghost":
        return { color: colors.primary };
      default:
        return { color: "#FFFFFF" };
    }
  };

  const getSizeStyle = (): ViewStyle => {
    switch (size) {
      case "small":
        return { paddingVertical: 10, paddingHorizontal: 16 };
      case "large":
        return { paddingVertical: 18, paddingHorizontal: 32 };
      default:
        return { paddingVertical: 14, paddingHorizontal: 24 };
    }
  };

  const getTextSizeStyle = (): TextStyle => {
    switch (size) {
      case "small":
        return { fontSize: 14 };
      case "large":
        return { fontSize: 18 };
      default:
        return { fontSize: 16 };
    }
  };

  const renderContent = () => {
    if (loading) {
      return (
        <ActivityIndicator
          color={
            variant === "outline" || variant === "ghost"
              ? colors.primary
              : "#FFFFFF"
          }
          size="small"
        />
      );
    }

    const iconElement = icon ? (
      <Text style={[styles.icon, iconPosition === "right" && styles.iconRight]}>
        {icon}
      </Text>
    ) : null;

    return (
      <View style={styles.content}>
        {iconPosition === "left" && iconElement}
        <Text
          style={[styles.text, getTextStyle(), getTextSizeStyle(), textStyle]}
        >
          {title}
        </Text>
        {iconPosition === "right" && iconElement}
      </View>
    );
  };

  return (
    <TouchableOpacity
      style={[
        styles.button,
        getButtonStyle(),
        getSizeStyle(),
        fullWidth && styles.fullWidth,
        style,
      ]}
      onPress={onPress}
      disabled={disabled || loading}
      activeOpacity={0.8}
    >
      {renderContent()}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  button: {
    borderRadius: 12,
    alignItems: "center",
    justifyContent: "center",
    minHeight: 48,
  },
  fullWidth: {
    width: "100%",
  },
  content: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
  },
  text: {
    fontWeight: "600",
  },
  icon: {
    fontSize: 18,
    marginRight: 8,
  },
  iconRight: {
    marginRight: 0,
    marginLeft: 8,
  },
});
