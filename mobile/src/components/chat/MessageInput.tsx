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

import React, { useState, useCallback, useRef, useEffect } from "react";
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
import { useChatStore } from "../../store/chatStore";

const MAX_LEN = 2000;
const TYPING_PULSE_MS = 2500;

interface MessageInputProps {
  onSend: (text: string) => void;
  disabled?: boolean;
  /** Show banner above input (e.g. "Reconnecting..."). */
  banner?: string | null;
  /** Pass the active room id to enable typing indicators. */
  roomId?: string;
}

function MessageInputComponent({
  onSend,
  disabled,
  banner,
  roomId,
}: MessageInputProps) {
  const [text, setText] = useState("");
  const layer = useAuthStore((s) => s.layer);
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];

  const startTyping = useChatStore((s) => s.startTyping);
  const stopTyping = useChatStore((s) => s.stopTyping);

  // Track whether we've already sent a typing_start so we don't spam the WS.
  const typingActiveRef = useRef(false);
  const pulseTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const fireStart = useCallback(() => {
    if (!roomId) return;
    if (!typingActiveRef.current) {
      typingActiveRef.current = true;
      startTyping(roomId);
    }
    // Pulse: re-send start every TYPING_PULSE_MS while user keeps typing —
    // server's 5s auto-clear will then drop us if we stop touching the field.
    if (pulseTimerRef.current) clearTimeout(pulseTimerRef.current);
    pulseTimerRef.current = setTimeout(() => {
      if (typingActiveRef.current && roomId) startTyping(roomId);
    }, TYPING_PULSE_MS);
  }, [roomId, startTyping]);

  const fireStop = useCallback(() => {
    if (!roomId) return;
    if (pulseTimerRef.current) {
      clearTimeout(pulseTimerRef.current);
      pulseTimerRef.current = null;
    }
    if (typingActiveRef.current) {
      typingActiveRef.current = false;
      stopTyping(roomId);
    }
  }, [roomId, stopTyping]);

  // Stop typing on unmount
  useEffect(() => {
    return () => {
      fireStop();
    };
  }, [fireStop]);

  const handleChange = useCallback(
    (next: string) => {
      const sliced = next.slice(0, MAX_LEN);
      setText(sliced);
      if (sliced.trim().length === 0) {
        fireStop();
      } else {
        fireStart();
      }
    },
    [fireStart, fireStop],
  );

  const canSend = !disabled && text.trim().length > 0;

  const handleSend = useCallback(() => {
    const trimmed = text.trim();
    if (!trimmed) return;
    haptics.light();
    onSend(trimmed);
    setText("");
    fireStop();
  }, [text, onSend, fireStop]);

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
          onChangeText={handleChange}
          placeholder="Type a message..."
          placeholderTextColor={colors.textSecondary}
          multiline
          maxLength={MAX_LEN}
          editable={!disabled}
          returnKeyType="default"
          textAlignVertical="center"
          onBlur={fireStop}
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
