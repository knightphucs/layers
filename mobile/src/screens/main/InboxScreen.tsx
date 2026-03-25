/**
 * LAYERS — InboxScreen
 * ==========================================
 * The Memory Inbox — where letters, replies, paper planes,
 * and time capsules arrive.
 *
 * Features:
 *   - Category filter pills (horizontal scroll)
 *   - FlatList with cursor-based infinite scroll
 *   - Pull-to-refresh
 *   - Unread badges
 *   - Sealed/opened letter card states
 *   - Stats bar (unread, pending replies)
 *   - Empty states per category
 *
 * DATA FLOW:
 *   InboxScreen → useInboxStore.fetchInbox()
 *     → inboxService.getInbox()
 *       → GET /artifacts/mine (MVP)
 *         → response transformed to InboxItem[]
 */

import React, { useEffect, useCallback, useMemo } from "react";
import {
  View,
  Text,
  FlatList,
  ActivityIndicator,
  StyleSheet,
  RefreshControl,
  TouchableOpacity,
  Alert,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useAuthStore } from "../../store/authStore";
import { useInboxStore } from "../../store/inboxStore";
import { Colors } from "../../constants/colors";
import { InboxItem, InboxCategory } from "../../types/inbox";
import LetterCard from "../../components/inbox/LetterCard";
import CategoryFilter from "../../components/inbox/CategoryFilter";
import EmptyInbox from "../../components/inbox/EmptyInbox";

// ============================================================
// INBOX SCREEN
// ============================================================

export default function InboxScreen() {
  const layer = useAuthStore((s) => s.layer);
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];

  // Inbox state
  const {
    items,
    stats,
    isLoading,
    isRefreshing,
    isLoadingMore,
    hasMore,
    error,
    unreadCount,
    filters,
    fetchInbox,
    fetchMore,
    refresh,
    fetchStats,
    markAsRead,
    setCategory,
    clearError,
  } = useInboxStore();

  // ========================================================
  // LIFECYCLE
  // ========================================================

  useEffect(() => {
    fetchInbox();
    fetchStats();
  }, []);

  // ========================================================
  // HANDLERS
  // ========================================================

  const handleLetterPress = useCallback(
    (item: InboxItem) => {
      // Mark as read (optimistic)
      if (!item.is_read) {
        markAsRead(item.id);
      }

      // Time capsule locked check
      if (
        item.artifact.content_type === "TIME_CAPSULE" &&
        item.artifact.unlock_at &&
        new Date(item.artifact.unlock_at) > new Date()
      ) {
        Alert.alert(
          "⏰ Time Capsule Locked",
          `This capsule opens on ${new Date(
            item.artifact.unlock_at,
          ).toLocaleDateString("vi-VN", {
            weekday: "long",
            year: "numeric",
            month: "long",
            day: "numeric",
          })}`,
          [{ text: "OK" }],
        );
        return;
      }

      // Geo-locked check
      if (item.artifact.is_locked && item.artifact.lock_reason === "distance") {
        Alert.alert(
          "🔒 Geo-Locked",
          `Walk within 50m of this artifact to read it.\nDistance: ${
            item.artifact.distance_meters
              ? Math.round(item.artifact.distance_meters) + "m"
              : "unknown"
          }`,
          [{ text: "Show on Map" }, { text: "OK" }],
        );
        return;
      }

      // TODO Week 5 Day 3: Open letter reader bottom sheet
      // For now, show alert with preview
      const payload = item.artifact.payload;
      const text =
        payload?.text ||
        payload?.caption ||
        payload?.title ||
        "No content available";
      Alert.alert(
        `${CONTENT_ICONS[item.artifact.content_type] || "📦"} ${
          CONTENT_LABELS[item.artifact.content_type] || "Artifact"
        }`,
        text.substring(0, 300),
        [
          {
            text: "Reply ✉️",
            onPress: () => handleReply(item),
          },
          { text: "Close" },
        ],
      );
    },
    [markAsRead],
  );

  const handleReply = useCallback((item: InboxItem) => {
    // TODO Week 5 Day 3: Open reply composer
    Alert.alert(
      "✉️ Slow Mail Reply",
      "Reply feature coming in Day 3! Your reply will take 6-12 hours to deliver.",
      [{ text: "OK" }],
    );
  }, []);

  const handleEmptyAction = useCallback(() => {
    // TODO: Navigate to Map or Create screen based on category
    Alert.alert("🗺️", "Head to the Map tab to explore your city!", [
      { text: "OK" },
    ]);
  }, []);

  const handleCategorySelect = useCallback(
    (category: InboxCategory | "all") => {
      setCategory(category);
    },
    [setCategory],
  );

  const handleEndReached = useCallback(() => {
    if (hasMore && !isLoadingMore) {
      fetchMore();
    }
  }, [hasMore, isLoadingMore, fetchMore]);

  // ========================================================
  // RENDER HELPERS
  // ========================================================

  const renderItem = useCallback(
    ({ item }: { item: InboxItem }) => (
      <LetterCard item={item} onPress={handleLetterPress} />
    ),
    [handleLetterPress],
  );

  const renderFooter = useCallback(() => {
    if (!isLoadingMore) return null;
    return (
      <View style={styles.loadingMore}>
        <ActivityIndicator size="small" color={colors.primary} />
        <Text style={[styles.loadingMoreText, { color: colors.textSecondary }]}>
          Loading more...
        </Text>
      </View>
    );
  }, [isLoadingMore, colors]);

  const renderEmpty = useCallback(() => {
    if (isLoading) return null;
    return (
      <EmptyInbox category={filters.category} onAction={handleEmptyAction} />
    );
  }, [isLoading, filters.category, handleEmptyAction]);

  const keyExtractor = useCallback((item: InboxItem) => item.id, []);

  // ========================================================
  // STATS BAR
  // ========================================================

  const statsBar = useMemo(() => {
    if (!stats) return null;
    return (
      <View style={[styles.statsBar, { backgroundColor: colors.surface }]}>
        <View style={styles.statItem}>
          <Text style={[styles.statNumber, { color: colors.text }]}>
            {stats.total_received}
          </Text>
          <Text style={[styles.statLabel, { color: colors.textSecondary }]}>
            Total
          </Text>
        </View>
        <View
          style={[styles.statDivider, { backgroundColor: colors.border }]}
        />
        <View style={styles.statItem}>
          <Text style={[styles.statNumber, { color: colors.primary }]}>
            {stats.unread_count}
          </Text>
          <Text style={[styles.statLabel, { color: colors.textSecondary }]}>
            Unread
          </Text>
        </View>
        <View
          style={[styles.statDivider, { backgroundColor: colors.border }]}
        />
        <View style={styles.statItem}>
          <Text style={[styles.statNumber, { color: colors.text }]}>
            {stats.replies_pending}
          </Text>
          <Text style={[styles.statLabel, { color: colors.textSecondary }]}>
            In Transit
          </Text>
        </View>
        <View
          style={[styles.statDivider, { backgroundColor: colors.border }]}
        />
        <View style={styles.statItem}>
          <Text style={[styles.statNumber, { color: colors.text }]}>
            {stats.paper_planes_found}
          </Text>
          <Text style={[styles.statLabel, { color: colors.textSecondary }]}>
            Planes
          </Text>
        </View>
      </View>
    );
  }, [stats, colors]);

  // ========================================================
  // ERROR STATE
  // ========================================================

  if (error && items.length === 0) {
    return (
      <SafeAreaView
        style={[styles.container, { backgroundColor: colors.background }]}
      >
        <View style={styles.errorContainer}>
          <Text style={styles.errorIcon}>⚠️</Text>
          <Text style={[styles.errorTitle, { color: colors.text }]}>
            Couldn't load inbox
          </Text>
          <Text style={[styles.errorMessage, { color: colors.textSecondary }]}>
            {error}
          </Text>
          <TouchableOpacity
            onPress={() => {
              clearError();
              fetchInbox();
            }}
            style={[styles.retryButton, { borderColor: colors.primary }]}
          >
            <Text style={[styles.retryText, { color: colors.primary }]}>
              Try Again
            </Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  // ========================================================
  // MAIN RENDER
  // ========================================================

  return (
    <SafeAreaView
      style={[styles.container, { backgroundColor: colors.background }]}
      edges={["top"]}
    >
      {/* Header */}
      <View style={styles.header}>
        <View>
          <Text style={[styles.headerTitle, { color: colors.text }]}>
            Memory Inbox
          </Text>
          <Text
            style={[styles.headerSubtitle, { color: colors.textSecondary }]}
          >
            {layer === "LIGHT" ? "☀️ Light Layer" : "🌙 Shadow Layer"}
          </Text>
        </View>
        {unreadCount > 0 && (
          <View
            style={[styles.unreadBadge, { backgroundColor: colors.primary }]}
          >
            <Text style={styles.unreadBadgeText}>
              {unreadCount > 99 ? "99+" : unreadCount}
            </Text>
          </View>
        )}
      </View>

      {/* Stats Bar */}
      {statsBar}

      {/* Category Filter */}
      <CategoryFilter
        selected={filters.category}
        onSelect={handleCategorySelect}
      />

      {/* Loading state (initial) */}
      {isLoading && items.length === 0 ? (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={colors.primary} />
          <Text style={[styles.loadingText, { color: colors.textSecondary }]}>
            Loading your memories...
          </Text>
        </View>
      ) : (
        /* Inbox List */
        <FlatList
          data={items}
          renderItem={renderItem}
          keyExtractor={keyExtractor}
          contentContainerStyle={[
            styles.listContent,
            items.length === 0 && styles.emptyListContent,
          ]}
          ListEmptyComponent={renderEmpty}
          ListFooterComponent={renderFooter}
          onEndReached={handleEndReached}
          onEndReachedThreshold={0.3}
          refreshControl={
            <RefreshControl
              refreshing={isRefreshing}
              onRefresh={refresh}
              tintColor={colors.primary}
              colors={[colors.primary]}
            />
          }
          showsVerticalScrollIndicator={false}
          // Performance optimizations (same pattern as Week 4 markers)
          removeClippedSubviews={true}
          maxToRenderPerBatch={10}
          windowSize={10}
          initialNumToRender={10}
          getItemLayout={(_data, index) => ({
            length: 110, // Approximate card height
            offset: 110 * index,
            index,
          })}
        />
      )}
    </SafeAreaView>
  );
}

// ============================================================
// CONTENT HELPERS (duplicated from LetterCard for Alert usage)
// ============================================================

const CONTENT_ICONS: Record<string, string> = {
  LETTER: "✉️",
  VOICE: "🎙️",
  PHOTO: "📷",
  PAPER_PLANE: "✈️",
  VOUCHER: "🎫",
  TIME_CAPSULE: "⏰",
  NOTEBOOK: "📓",
};

const CONTENT_LABELS: Record<string, string> = {
  LETTER: "Letter",
  VOICE: "Voice Memo",
  PHOTO: "Photo Memory",
  PAPER_PLANE: "Paper Plane",
  VOUCHER: "Voucher",
  TIME_CAPSULE: "Time Capsule",
  NOTEBOOK: "Notebook",
};

// ============================================================
// STYLES
// ============================================================

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 16,
    paddingTop: 8,
    paddingBottom: 4,
  },
  headerTitle: {
    fontSize: 28,
    fontWeight: "bold",
    letterSpacing: -0.5,
  },
  headerSubtitle: {
    fontSize: 13,
    marginTop: 2,
  },
  unreadBadge: {
    minWidth: 28,
    height: 28,
    borderRadius: 14,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 8,
  },
  unreadBadgeText: {
    color: "#FFFFFF",
    fontSize: 13,
    fontWeight: "700",
  },
  statsBar: {
    flexDirection: "row",
    marginHorizontal: 16,
    marginTop: 8,
    borderRadius: 12,
    paddingVertical: 10,
    paddingHorizontal: 4,
  },
  statItem: {
    flex: 1,
    alignItems: "center",
  },
  statNumber: {
    fontSize: 18,
    fontWeight: "600",
  },
  statLabel: {
    fontSize: 11,
    marginTop: 2,
  },
  statDivider: {
    width: 1,
    height: 28,
    alignSelf: "center",
  },
  listContent: {
    paddingTop: 8,
    paddingBottom: 20,
  },
  emptyListContent: {
    flexGrow: 1,
  },
  loadingContainer: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  loadingText: {
    marginTop: 12,
    fontSize: 14,
  },
  loadingMore: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: 16,
    gap: 8,
  },
  loadingMoreText: {
    fontSize: 13,
  },
  errorContainer: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 32,
  },
  errorIcon: {
    fontSize: 48,
    marginBottom: 12,
  },
  errorTitle: {
    fontSize: 18,
    fontWeight: "600",
    marginBottom: 8,
  },
  errorMessage: {
    fontSize: 14,
    textAlign: "center",
    marginBottom: 20,
  },
  retryButton: {
    paddingHorizontal: 24,
    paddingVertical: 10,
    borderRadius: 10,
    borderWidth: 1.5,
  },
  retryText: {
    fontSize: 14,
    fontWeight: "600",
  },
});
