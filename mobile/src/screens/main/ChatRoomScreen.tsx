/**
 * LAYERS — ChatRoomScreen
 * =======================================
 * Full chat screen for a single DIRECT room.
 *
 * - Mounts → opens WS via chatStore.openChatWithRoom
 * - Unmounts → calls chatStore.leaveChat (closes WS)
 * - Shows ChatHeader, MessageList (inverted), MessageInput
 * - Handles connection state banners
 */

import React, { useEffect, useMemo, useCallback } from "react";
import {
  View,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
} from "react-native";
import { Colors } from "../../constants/colors";
import { useAuthStore } from "../../store/authStore";
import { useChatStore } from "../../store/chatStore";
import {
  ChatHeader,
  MessageList,
  MessageInput,
  EmptyChatRoom,
  TypingIndicator,
} from "../../components/chat";
import { ChatMessageWithStatus } from "../../types/chat";

interface ChatRoomScreenProps {
  roomId: string;
  onBack: () => void;
}

const EMPTY_MESSAGES: ChatMessageWithStatus[] = [];

export default function ChatRoomScreen({
  roomId,
  onBack,
}: ChatRoomScreenProps) {
  const layer = useAuthStore((s) => s.layer);
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];
  const user = useAuthStore((s) => s.user);

  const room = useChatStore((s) => s.rooms.find((r) => r.id === roomId));
  const messages = useChatStore(
    (s) => s.messagesByRoom[roomId] ?? EMPTY_MESSAGES,
  );
  const wsState = useChatStore((s) => s.wsState);
  const hasMore = useChatStore((s) => s.hasMoreByRoom[roomId] ?? true);
  const isLoadingMessages = useChatStore((s) => s.isLoadingMessages);

  const openChatWithRoom = useChatStore((s) => s.openChatWithRoom);
  const leaveChat = useChatStore((s) => s.leaveChat);
  const sendMessage = useChatStore((s) => s.sendMessage);
  const loadOlderMessages = useChatStore((s) => s.loadOlderMessages);

  // Mount: open WS. Unmount: close.
  useEffect(() => {
    if (!user) return;
    openChatWithRoom(roomId, user.id);
    return () => {
      leaveChat();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [roomId, user?.id]);

  const handleBack = useCallback(() => {
    leaveChat();
    onBack();
  }, [leaveChat, onBack]);

  const handleSend = useCallback(
    (text: string) => {
      if (!user) return;
      sendMessage(roomId, text, user.id);
    },
    [roomId, user, sendMessage],
  );

  const handleLoadMore = useCallback(() => {
    loadOlderMessages(roomId);
  }, [roomId, loadOlderMessages]);

  const banner = useMemo(() => {
    if (wsState === "connecting" || wsState === "reconnecting") {
      return wsState === "reconnecting" ? "🔄 Reconnecting…" : "Connecting…";
    }
    if (wsState === "closed") {
      return "Connection lost — your messages will send via REST";
    }
    return null;
  }, [wsState]);

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <ChatHeader
        username={room?.other_user?.username}
        avatarUrl={room?.other_user?.avatar_url}
        wsState={wsState}
        onBack={handleBack}
      />

      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
        keyboardVerticalOffset={Platform.OS === "ios" ? 0 : 0}
      >
        {messages.length === 0 ? (
          isLoadingMessages ? (
            <View style={styles.loadingContainer}>
              <ActivityIndicator size="large" color={colors.primary} />
            </View>
          ) : (
            <EmptyChatRoom />
          )
        ) : (
          <MessageList
            messages={messages}
            currentUserId={user?.id || ""}
            isLoadingMore={isLoadingMessages}
            hasMore={hasMore}
            onLoadMore={handleLoadMore}
          />
        )}
        <TypingIndicator roomId={roomId} />
        <MessageInput
          onSend={handleSend}
          banner={banner}
          disabled={!user}
          roomId={roomId}
        />
      </KeyboardAvoidingView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  flex: {
    flex: 1,
  },
  loadingContainer: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
  },
});
