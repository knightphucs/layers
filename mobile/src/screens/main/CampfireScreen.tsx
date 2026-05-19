/**
 * LAYERS — CampfireScreen
 * ========================================
 * Full screen for a campfire chat room.
 *
 * Layout:  CampfireHeader → MembersList → MessageList → MessageInput
 *
 * Lifecycle:
 *   - Mounts → opens WS via openChatWithRoom + refreshMembers
 *   - Unmounts → leaveChat (closes WS, but does NOT leave the campfire —
 *     the user stays a member until they explicitly tap "Leave fire")
 *   - "Leave fire" → confirm dialog → chatStore.leaveCampfire → onBack()
 *
 * Reuses MessageList + MessageInput.
 */

import React, { useEffect, useMemo, useCallback } from "react";
import {
  View,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
  Alert,
} from "react-native";
import { Colors } from "../../constants/colors";
import { useAuthStore } from "../../store/authStore";
import { useChatStore } from "../../store/chatStore";
import {
  CampfireHeader,
  MembersList,
  MessageList,
  MessageInput,
  EmptyChatRoom,
} from "../../components/chat";
import { CampfireMemberInfo, ChatMessageWithStatus } from "../../types/chat";

interface CampfireScreenProps {
  roomId: string;
  onBack: () => void;
}

const EMPTY_MESSAGES: ChatMessageWithStatus[] = [];
const EMPTY_MEMBERS: CampfireMemberInfo[] = [];

export default function CampfireScreen({
  roomId,
  onBack,
}: CampfireScreenProps) {
  const layer = useAuthStore((s) => s.layer);
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];
  const user = useAuthStore((s) => s.user);

  const room = useChatStore((s) => s.rooms.find((r) => r.id === roomId));
  const messages = useChatStore(
    (s) => s.messagesByRoom[roomId] ?? EMPTY_MESSAGES,
  );
  const members = useChatStore((s) => s.membersByRoom[roomId] ?? EMPTY_MEMBERS);
  const wsState = useChatStore((s) => s.wsState);
  const hasMore = useChatStore((s) => s.hasMoreByRoom[roomId] ?? true);
  const isLoadingMessages = useChatStore((s) => s.isLoadingMessages);

  const openChatWithRoom = useChatStore((s) => s.openChatWithRoom);
  const leaveChat = useChatStore((s) => s.leaveChat);
  const leaveCampfire = useChatStore((s) => s.leaveCampfire);
  const sendMessage = useChatStore((s) => s.sendMessage);
  const loadOlderMessages = useChatStore((s) => s.loadOlderMessages);
  const refreshMembers = useChatStore((s) => s.refreshMembers);

  // Mount: open WS + load members. Unmount: close WS (but stay a member).
  useEffect(() => {
    if (!user) return;
    openChatWithRoom(roomId, user.id);
    refreshMembers(roomId);
    return () => {
      leaveChat();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [roomId, user?.id]);

  // Derived counts
  const onlineCount = useMemo(
    () => members.filter((m) => m.is_online).length,
    [members],
  );

  const handleBack = useCallback(() => {
    leaveChat();
    onBack();
  }, [leaveChat, onBack]);

  // "Leave fire" — explicit leave with confirmation
  const handleLeave = useCallback(() => {
    Alert.alert(
      "Leave this campfire?",
      "You'll stop receiving messages from this fire. You can rejoin later if you're still nearby.",
      [
        { text: "Stay", style: "cancel" },
        {
          text: "Leave fire 🔥",
          style: "destructive",
          onPress: async () => {
            await leaveCampfire(roomId);
            onBack();
          },
        },
      ],
    );
  }, [roomId, leaveCampfire, onBack]);

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
    if (wsState === "reconnecting") return "🔄 Reconnecting…";
    if (wsState === "connecting") return "Connecting…";
    if (wsState === "closed") {
      return "Connection lost — messages will send via REST";
    }
    return null;
  }, [wsState]);

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <CampfireHeader
        name={room?.name ?? null}
        expiresAt={room?.expires_at ?? null}
        memberCount={members.length}
        onlineCount={onlineCount}
        onBack={handleBack}
        onLeave={handleLeave}
      />

      <MembersList members={members} />

      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
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

        <MessageInput onSend={handleSend} banner={banner} disabled={!user} />
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
