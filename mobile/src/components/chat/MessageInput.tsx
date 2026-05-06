/**
 * LAYERS — MessageInput Component
 * ================================================
 * Text input + send button at the bottom of the chat screen.
 *
 * - 2000 char limit (matches backend)
 * - Send button disabled while empty
 * - Auto-grows up to 4 lines, then scrolls
 * - Keyboard handled by parent (KeyboardAvoidingView wrapping)
 */

import React, { useState, useCallback } from "react";
import {
  View,
  TextInput,
  TouchableOpacity,
  Text,
  StyleSheet,
  Platform,
} from "react-native";
import { Colors } from "../../constants/colors";
import { useAuthStore } from "../../store/authStore";
import { haptics } from "../../utils/haptics";

const MAX_LEN = 2000;

interface MessageInputProps {
  onSend: (text: string) => void;
  disabled?: boolean;
  /** Show banner above input (e.g. "Reconnecting..."). */
  banner?: string | null;
}

function MessageInputComponent({
  onSend,
  disabled,
  banner,
}: MessageInputProps) {
  const [text, setText] = useState("");
  const layer = useAuthStore((s) => s.layer);
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];

  const canSend = !disabled && text.trim().length > 0;

  const handleSend = useCallback(() => {
    const trimmed = text.trim();
    if (!trimmed) return;
    haptics.light();
    onSend(trimmed);
    setText("");
  }, [text, onSend]);

  return (
    <View
      style={[
        styles.container,
        {
          backgroundColor: colors.surface,
          borderTopColor: colors.border,
        },
      ]}
    >
      {banner && (
        <View
          style={[styles.banner, { backgroundColor: colors.border + "40" }]}
        >
          <Text style={[styles.bannerText, { color: colors.textSecondary }]}>
            {banner}
          </Text>
        </View>
      )}

      <View style={styles.inputRow}>
        <TextInput
          style={[
            styles.input,
            {
              backgroundColor: colors.background,
              color: colors.text,
              borderColor: colors.border,
            },
          ]}
          value={text}
          onChangeText={(t) => setText(t.slice(0, MAX_LEN))}
          placeholder="Type a message..."
          placeholderTextColor={colors.textSecondary}
          multiline
          maxLength={MAX_LEN}
          editable={!disabled}
          returnKeyType="default"
          textAlignVertical="center"
        />

        <TouchableOpacity
          onPress={handleSend}
          disabled={!canSend}
          style={[
            styles.sendBtn,
            {
              backgroundColor: canSend ? colors.primary : colors.border,
            },
          ]}
          activeOpacity={0.7}
        >
          <Text style={styles.sendIcon}>↑</Text>
        </TouchableOpacity>
      </View>

      {text.length > MAX_LEN * 0.85 && (
        <Text
          style={[
            styles.charCounter,
            {
              color: text.length >= MAX_LEN ? "#FF6B6B" : colors.textSecondary,
            },
          ]}
        >
          {text.length}/{MAX_LEN}
        </Text>
      )}
    </View>
  );
}

export const MessageInput = React.memo(MessageInputComponent);
MessageInput.displayName = "MessageInput";

const styles = StyleSheet.create({
  container: {
    borderTopWidth: 1,
    paddingTop: 6,
    paddingBottom: Platform.OS === "ios" ? 6 : 8,
    paddingHorizontal: 10,
  },
  banner: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
    marginBottom: 6,
    alignItems: "center",
  },
  bannerText: {
    fontSize: 12,
  },
  inputRow: {
    flexDirection: "row",
    alignItems: "flex-end",
    gap: 8,
  },
  input: {
    flex: 1,
    minHeight: 40,
    maxHeight: 120,
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderWidth: 1,
    borderRadius: 22,
    fontSize: 15,
  },
  sendBtn: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: "center",
    justifyContent: "center",
  },
  sendIcon: {
    color: "#FFFFFF",
    fontSize: 22,
    fontWeight: "700",
    marginTop: -2,
  },
  charCounter: {
    fontSize: 11,
    textAlign: "right",
    marginTop: 4,
    marginRight: 8,
  },
});

export default MessageInput;
