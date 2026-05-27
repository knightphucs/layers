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

import React, { useEffect, useMemo, useCallback, useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
  Alert,
  TouchableOpacity,
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
  TypingIndicator,
} from "../../components/chat";
import { CampfireMemberInfo, ChatMessageWithStatus } from "../../types/chat";
import { useGameStore } from "../../store/gameStore";
import { GamePanel } from "../../components/game";

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

  const activeGame = useGameStore((s) => s.game);
  const hasActiveGame =
    !!activeGame &&
    activeGame.state !== "COMPLETED" &&
    activeGame.room_id === roomId;

  const [gameOpen, setGameOpen] = useState<boolean>(false);

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

  // Auto-open the drawer when a game becomes active (started by anyone in the room).
  useEffect(() => {
    if (hasActiveGame) setGameOpen(true);
  }, [hasActiveGame]);

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

  // Game drawer toggle row — also acts as an entry point if no game is running
  const renderGameToggle = () => (
    <TouchableOpacity
      onPress={() => setGameOpen((v) => !v)}
      activeOpacity={0.7}
      style={[
        styles.gameToggle,
        {
          backgroundColor: colors.surface,
          borderColor: colors.border,
        },
      ]}
    >
      <Text style={[styles.gameToggleText, { color: colors.text }]}>
        {hasActiveGame
          ? "🔥 Truth or Dare — round in progress"
          : "🔥 Truth or Dare"}
      </Text>
      <Text style={[styles.gameToggleChevron, { color: colors.textSecondary }]}>
        {gameOpen ? "▲" : "▼"}
      </Text>
    </TouchableOpacity>
  );

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

      {renderGameToggle()}

      {gameOpen && (
        <View style={[styles.gameDrawer, { borderColor: colors.border }]}>
          <GamePanel roomId={roomId} />
        </View>
      )}

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
  gameToggle: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderTopWidth: 1,
    borderBottomWidth: 1,
  },
  gameToggleText: { fontSize: 14, fontWeight: "600" },
  gameToggleChevron: { fontSize: 12 },
  gameDrawer: {
    borderBottomWidth: 1,
    height: 360,
  },
});
