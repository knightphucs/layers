// ===========================================
// Styled text input with label and error support
// ===========================================

import React, { useState } from "react";
import {
  View,
  TextInput,
  Text,
  StyleSheet,
  TextInputProps,
  ViewStyle,
  TouchableOpacity,
  Animated,
} from "react-native";
import { Colors } from "../constants/colors";
import { useAuthStore } from "../store/authStore";

interface InputProps extends TextInputProps {
  label?: string;
  error?: string;
  hint?: string;
  containerStyle?: ViewStyle;
  leftIcon?: string | React.ReactNode;
  rightIcon?: string | React.ReactNode;
  onRightIconPress?: () => void;
}

export default function Input({
  label,
  error,
  hint,
  containerStyle,
  leftIcon,
  rightIcon,
  onRightIconPress,
  onFocus,
  onBlur,
  ...props
}: InputProps) {
  const [isFocused, setIsFocused] = useState(false);
  const layer = useAuthStore((state) => state.layer);
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];

  const handleFocus = (e: any) => {
    setIsFocused(true);
    onFocus?.(e);
  };

  const handleBlur = (e: any) => {
    setIsFocused(false);
    onBlur?.(e);
  };

  return (
    <View style={[styles.container, containerStyle]}>
      {/* Label */}
      {label && (
        <Text style={[styles.label, { color: colors.text }]}>{label}</Text>
      )}

      {/* Input Container */}
      <View
        style={[
          styles.inputContainer,
          {
            backgroundColor: colors.surface,
            borderColor: error
              ? colors.error
              : isFocused
                ? colors.primary
                : colors.border,
          },
          isFocused && styles.inputFocused,
          error && styles.inputError,
        ]}
      >
        {/* Left Icon Rendering */}
        {leftIcon && (
          <View style={styles.leftIconWrapper}>
            {typeof leftIcon === "string" ? (
              <Text style={styles.iconText}>{leftIcon}</Text>
            ) : (
              leftIcon
            )}
          </View>
        )}

        {/* Text Input */}
        <TextInput
          style={[
            styles.input,
            { color: colors.text },
            !leftIcon && { paddingLeft: 16 }, // Adjust padding if no icon
          ]}
          placeholderTextColor={colors.textSecondary}
          onFocus={handleFocus}
          onBlur={handleBlur}
          {...props}
        />

        {/* Right Icon Rendering */}
        {rightIcon && (
          <TouchableOpacity
            onPress={onRightIconPress}
            style={styles.rightIconButton}
            activeOpacity={0.7}
          >
            {typeof rightIcon === "string" ? (
              <Text style={styles.iconText}>{rightIcon}</Text>
            ) : (
              rightIcon
            )}
          </TouchableOpacity>
        )}
      </View>

      {/* Error Message */}
      {error && (
        <View style={styles.errorContainer}>
          <Text style={styles.errorIcon}>⚠️</Text>
          <Text style={[styles.error, { color: colors.error }]}>{error}</Text>
        </View>
      )}

      {/* Hint */}
      {hint && !error && (
        <Text style={[styles.hint, { color: colors.textSecondary }]}>
          {hint}
        </Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginBottom: 20,
  },
  label: {
    fontSize: 14,
    fontWeight: "600",
    marginBottom: 8,
  },
  inputContainer: {
    flexDirection: "row",
    alignItems: "center",
    borderWidth: 1.5,
    borderRadius: 12,
    overflow: "hidden",
  },
  inputFocused: {
    borderWidth: 2,
  },
  inputError: {
    borderWidth: 2,
  },
  input: {
    flex: 1,
    paddingHorizontal: 16,
    paddingVertical: 14,
    fontSize: 16,
  },
  leftIconWrapper: {
    paddingLeft: 16,
    paddingRight: 8,
    justifyContent: "center",
  },
  rightIconButton: {
    padding: 12,
    justifyContent: "center",
  },
  iconText: {
    fontSize: 20,
  },
  errorContainer: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: 6,
  },
  errorIcon: {
    fontSize: 12,
    marginRight: 4,
  },
  error: {
    fontSize: 13,
  },
  hint: {
    fontSize: 12,
    marginTop: 6,
  },
});
