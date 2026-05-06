/**
 * LAYERS — ChatListScreen
 * =======================================
 * List view of all the user's chat rooms.
 *
 * Tapping a room opens ChatRoomScreen (rendered conditionally by parent
 * based on chatStore.activeRoomId).
 */

import React, { useEffect, useCallback } from "react";
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  RefreshControl,
  ActivityIndicator,
  StyleSheet,
  Image,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { Colors } from "../../constants/colors";
import { useAuthStore } from "../../store/authStore";
import { useChatStore } from "../../store/chatStore";
import { ChatRoomItem } from "../../types/chat";
import { EmptyChatList } from "../../components/chat";

// ============================================================
// HELPERS
// ============================================================

function timeAgo(iso: string): string {
  const now = Date.now();
  const t = new Date(iso).getTime();
  const diff = Math.max(0, now - t);
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "now";
  if (mins < 60) return `${mins}m`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d`;
  const date = new Date(iso);
  return date.toLocaleDateString("vi-VN", { day: "2-digit", month: "short" });
}

// ============================================================
// ROW
// ============================================================

interface RowProps {
  room: ChatRoomItem;
  onPress: () => void;
}

const ChatRow = React.memo(function ChatRow({ room, onPress }: RowProps) {
  const layer = useAuthStore((s) => s.layer);
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];

  const username = room.other_user?.username || "Anonymous";
  const initial = username[0]?.toUpperCase() || "?";

  return (
    <TouchableOpacity
      onPress={onPress}
      activeOpacity={0.6}
      style={[
        styles.row,
        { backgroundColor: colors.surface, borderColor: colors.border },
      ]}
    >
      {room.other_user?.avatar_url ? (
        <Image
          source={{ uri: room.other_user.avatar_url }}
          style={styles.avatar}
        />
      ) : (
        <View
          style={[
            styles.avatarPlaceholder,
            { backgroundColor: colors.primary + "20" },
          ]}
        >
          <Text style={[styles.avatarInitial, { color: colors.primary }]}>
            {initial}
          </Text>
        </View>
      )}

      <View style={styles.middle}>
        <View style={styles.topRow}>
          <Text
            numberOfLines={1}
            style={[styles.username, { color: colors.text }]}
          >
            {username}
          </Text>
          <Text style={[styles.time, { color: colors.textSecondary }]}>
            {timeAgo(room.last_activity_at)}
          </Text>
        </View>
        <Text
          numberOfLines={1}
          style={[styles.preview, { color: colors.textSecondary }]}
        >
          {room.last_message_preview || "No messages yet"}
        </Text>
      </View>
    </TouchableOpacity>
  );
});

// ============================================================
// SCREEN
// ============================================================

interface ChatListScreenProps {
  onBack: () => void;
  /** Called when a room row is tapped (parent should render ChatRoomScreen). */
  onOpenRoom: (roomId: string) => void;
}

export default function ChatListScreen({
  onBack,
  onOpenRoom,
}: ChatListScreenProps) {
  const layer = useAuthStore((s) => s.layer);
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];
  const user = useAuthStore((s) => s.user);

  const rooms = useChatStore((s) => s.rooms);
  const isLoading = useChatStore((s) => s.isLoadingRooms);
  const error = useChatStore((s) => s.error);
  const fetchRooms = useChatStore((s) => s.fetchRooms);

  useEffect(() => {
    if (user) fetchRooms(user.id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user?.id]);

  const handleRefresh = useCallback(() => {
    if (user) fetchRooms(user.id);
  }, [user, fetchRooms]);

  const keyExtractor = useCallback((item: ChatRoomItem) => item.id, []);

  return (
    <SafeAreaView
      edges={["top"]}
      style={[styles.container, { backgroundColor: colors.background }]}
    >
      {/* Header */}
      <View style={[styles.header, { borderBottomColor: colors.border }]}>
        <TouchableOpacity
          onPress={onBack}
          style={styles.backBtn}
          hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
        >
          <Text style={[styles.backIcon, { color: colors.text }]}>‹</Text>
        </TouchableOpacity>
        <Text style={[styles.title, { color: colors.text }]}>Messages</Text>
        <View style={styles.headerSpacer} />
      </View>

      {error && (
        <View style={styles.errorBanner}>
          <Text style={styles.errorText}>{error}</Text>
        </View>
      )}

      {isLoading && rooms.length === 0 ? (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={colors.primary} />
        </View>
      ) : rooms.length === 0 ? (
        <EmptyChatList />
      ) : (
        <FlatList
          data={rooms}
          keyExtractor={keyExtractor}
          renderItem={({ item }) => (
            <ChatRow room={item} onPress={() => onOpenRoom(item.id)} />
          )}
          refreshControl={
            <RefreshControl
              refreshing={isLoading}
              onRefresh={handleRefresh}
              tintColor={colors.primary}
            />
          }
          contentContainerStyle={{ paddingVertical: 8 }}
        />
      )}
    </SafeAreaView>
  );
}

// ============================================================
// STYLES
// ============================================================

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 8,
    paddingVertical: 12,
    borderBottomWidth: 1,
  },
  backBtn: {
    width: 40,
    height: 40,
    alignItems: "center",
    justifyContent: "center",
  },
  backIcon: {
    fontSize: 32,
    fontWeight: "300",
    marginTop: -4,
  },
  title: {
    flex: 1,
    fontSize: 18,
    fontWeight: "600",
    textAlign: "center",
  },
  headerSpacer: {
    width: 40,
  },
  errorBanner: {
    backgroundColor: "#FEE2E2",
    paddingVertical: 8,
    paddingHorizontal: 16,
  },
  errorText: {
    color: "#991B1B",
    fontSize: 13,
  },
  loadingContainer: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  row: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 12,
    paddingHorizontal: 14,
    marginHorizontal: 12,
    marginVertical: 4,
    borderRadius: 12,
    borderWidth: 1,
    gap: 12,
  },
  avatar: {
    width: 48,
    height: 48,
    borderRadius: 24,
  },
  avatarPlaceholder: {
    width: 48,
    height: 48,
    borderRadius: 24,
    alignItems: "center",
    justifyContent: "center",
  },
  avatarInitial: {
    fontSize: 20,
    fontWeight: "600",
  },
  middle: {
    flex: 1,
  },
  topRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 2,
  },
  username: {
    flex: 1,
    fontSize: 15,
    fontWeight: "600",
    marginRight: 8,
  },
  time: {
    fontSize: 11,
  },
  preview: {
    fontSize: 13,
  },
});
