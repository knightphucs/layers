/**
 * LAYERS — MessagesContainer
 * ==========================================
 * Lightweight switcher between ChatListScreen and ChatRoomScreen,
 * driven by chatStore.activeRoomId.
 *
 * USAGE (inside ProfileScreen):
 *   {showMessages && (
 *     <MessagesContainer onBack={() => setShowMessages(false)} />
 *   )}
 *
 * This container also handles deep-link entry from elsewhere:
 * if some other code path sets chatStore.activeRoomId before
 * mounting this container, ChatRoomScreen renders directly.
 */

import React, { useState, useCallback } from "react";
import { View, StyleSheet } from "react-native";
import { useChatStore } from "../../store/chatStore";
import ChatListScreen from "./ChatListScreen";
import ChatRoomScreen from "./ChatRoomScreen";

interface MessagesContainerProps {
  onBack: () => void;
}

export default function MessagesContainer({ onBack }: MessagesContainerProps) {
  const activeRoomId = useChatStore((s) => s.activeRoomId);
  const leaveChat = useChatStore((s) => s.leaveChat);

  // Local state to allow opening a room from the list before the store updates
  const [pendingRoomId, setPendingRoomId] = useState<string | null>(null);
  const currentRoomId = activeRoomId || pendingRoomId;

  const handleOpenRoom = useCallback((roomId: string) => {
    setPendingRoomId(roomId);
  }, []);

  const handleBackFromRoom = useCallback(() => {
    setPendingRoomId(null);
    leaveChat();
  }, [leaveChat]);

  return (
    <View style={styles.container}>
      {currentRoomId ? (
        <ChatRoomScreen roomId={currentRoomId} onBack={handleBackFromRoom} />
      ) : (
        <ChatListScreen onBack={onBack} onOpenRoom={handleOpenRoom} />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
});
