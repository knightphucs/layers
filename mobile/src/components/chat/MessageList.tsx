/**
 * LAYERS — MessageList Component
 * ===============================================
 * Inverted FlatList that renders chat messages newest-first at the bottom.
 *
 * Key behaviors:
 *   - inverted=true → newest at the visual bottom, scrollbar starts at bottom
 *   - onEndReached fires when user scrolls UP toward older messages
 *   - keyExtractor uses message.id (or client_id for optimistic ones)
 *   - React.memo on MessageBubble (handled in MessageBubble.tsx)
 */

import React, { useCallback, useMemo } from "react";
import {
  FlatList,
  View,
  ActivityIndicator,
  StyleSheet,
  ListRenderItem,
} from "react-native";
import { Colors } from "../../constants/colors";
import { useAuthStore } from "../../store/authStore";
import { ChatMessageWithStatus } from "../../types/chat";
import MessageBubble from "./MessageBubble";

interface MessageListProps {
  messages: ChatMessageWithStatus[];
  currentUserId: string;
  isLoadingMore?: boolean;
  hasMore?: boolean;
  onLoadMore?: () => void;
}

function MessageListComponent({
  messages,
  currentUserId,
  isLoadingMore,
  hasMore,
  onLoadMore,
}: MessageListProps) {
  const layer = useAuthStore((s) => s.layer);
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];

  const keyExtractor = useCallback(
    (item: ChatMessageWithStatus) => item.client_id || item.id,
    [],
  );

  // Group messages by sender + time-bucket (within 60s of next from same sender → no time)
  const renderItem: ListRenderItem<ChatMessageWithStatus> = useCallback(
    ({ item, index }) => {
      // Because list is inverted: index 0 is newest. The "next" newer message is at index-1
      // (which doesn't exist for index 0). The "previous" message in time is at index+1.
      const previous = messages[index + 1]; // older message in time
      const showTime =
        !previous ||
        previous.sender_id !== item.sender_id ||
        Math.abs(
          new Date(item.created_at).getTime() -
            new Date(previous.created_at).getTime(),
        ) > 60_000;

      return (
        <MessageBubble
          message={item}
          isMine={item.sender_id === currentUserId}
          showTime={showTime}
        />
      );
    },
    [messages, currentUserId],
  );

  const ListFooter = useMemo(
    () =>
      isLoadingMore ? (
        <View style={styles.loaderRow}>
          <ActivityIndicator size="small" color={colors.primary} />
        </View>
      ) : null,
    [isLoadingMore, colors.primary],
  );

  return (
    <FlatList
      data={messages}
      renderItem={renderItem}
      keyExtractor={keyExtractor}
      inverted
      contentContainerStyle={styles.content}
      onEndReached={hasMore ? onLoadMore : undefined}
      onEndReachedThreshold={0.4}
      ListFooterComponent={ListFooter}
      removeClippedSubviews
      maxToRenderPerBatch={20}
      windowSize={10}
      initialNumToRender={20}
      keyboardShouldPersistTaps="handled"
    />
  );
}

export const MessageList = React.memo(MessageListComponent);
MessageList.displayName = "MessageList";

const styles = StyleSheet.create({
  content: {
    paddingVertical: 8,
  },
  loaderRow: {
    paddingVertical: 16,
    alignItems: "center",
  },
});

export default MessageList;
