/**
 * LAYERS — ConnectionsScreen
 * ==========================================
 * The social heart of LAYERS — where strangers become friends.
 *
 * Sections:
 *   1. Header with title + pending request badge
 *   2. Stats bar (Strangers | Signals | Connected)
 *   3. Level filter pills
 *   4. FlatList of ConnectionCard items
 *
 * NAVIGATION:
 *   Accessed from Profile → Connections menu item
 *   (Will become its own tab in Week 6)
 *
 */

import React, { useEffect, useCallback, useState, useMemo } from "react";
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
import { useChatStore } from "../../store/chatStore";
import { useConnectionStore } from "../../store/connectionStore";
import { Colors } from "../../constants/colors";
import { ConnectionItem, ConnectionLevel } from "../../types/connections";
import {
  ConnectionCard,
  LevelFilter,
  EmptyConnections,
} from "../../components/connections";

// ============================================================
// SCREEN
// ============================================================

interface Props {
  onBack?: () => void;
  onOpenMessages?: () => void;
}

export default function ConnectionsScreen({ onBack, onOpenMessages }: Props) {
  const layer = useAuthStore((s) => s.layer);
  const currentUser = useAuthStore((s) => s.user);
  const openChatWithUser = useChatStore((s) => s.openChatWithUser);
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];

  const {
    connections,
    total,
    strangersCount,
    signalsCount,
    connectedCount,
    filter,
    isLoading,
    isRefreshing,
    error,
    fetchConnections,
    refresh,
    setFilter,
    requestUpgrade,
    acceptUpgrade,
    rejectUpgrade,
    clearError,
  } = useConnectionStore();

  // Track which connection is currently being processed (for loading state)
  const [processingId, setProcessingId] = useState<string | null>(null);

  // ========================================================
  // LIFECYCLE
  // ========================================================

  useEffect(() => {
    fetchConnections();
  }, []);

  // ========================================================
  // HANDLERS
  // ========================================================

  const handleRequestUpgrade = useCallback(
    async (connectionId: string) => {
      setProcessingId(connectionId);
      try {
        const upgraded = await requestUpgrade(connectionId);
        if (upgraded) {
          Alert.alert(
            "✨ Connected!",
            "You're now connected! Realtime chat will unlock in Week 6.",
            [{ text: "Amazing!" }],
          );
        } else {
          Alert.alert(
            "Request Sent",
            "Your connection request has been sent. Waiting for them to accept.",
            [{ text: "OK" }],
          );
        }
      } finally {
        setProcessingId(null);
      }
    },
    [requestUpgrade],
  );

  const handleAccept = useCallback(
    async (connectionId: string) => {
      setProcessingId(connectionId);
      try {
        const upgraded = await acceptUpgrade(connectionId);
        if (upgraded) {
          Alert.alert(
            "✨ Connected!",
            "You accepted the connection! Realtime chat coming soon.",
            [{ text: "Let's go!" }],
          );
        }
      } finally {
        setProcessingId(null);
      }
    },
    [acceptUpgrade],
  );

  const handleReject = useCallback(
    async (connectionId: string) => {
      Alert.alert(
        "Decline Connection?",
        "They won't be notified. You can still exchange letters.",
        [
          { text: "Cancel", style: "cancel" },
          {
            text: "Decline",
            style: "destructive",
            onPress: async () => {
              setProcessingId(connectionId);
              await rejectUpgrade(connectionId);
              setProcessingId(null);
            },
          },
        ],
      );
    },
    [rejectUpgrade],
  );

  const handleMessage = useCallback(
    async (connectionId: string) => {
      const connection = connections.find((c) => c.id === connectionId);
      const otherUserId = connection?.other_user?.id;

      if (!currentUser || !otherUserId) {
        Alert.alert("Messages", "Unable to open this conversation right now.", [
          { text: "OK" },
        ]);
        return;
      }

      setProcessingId(connectionId);
      try {
        const roomId = await openChatWithUser(otherUserId, currentUser.id);
        if (roomId) {
          onOpenMessages?.();
        }
      } finally {
        setProcessingId(null);
      }
    },
    [connections, currentUser, onOpenMessages, openChatWithUser],
  );

  const handleFilterSelect = useCallback(
    (f: ConnectionLevel | "all") => {
      setFilter(f);
    },
    [setFilter],
  );

  // ========================================================
  // RENDER HELPERS
  // ========================================================

  const renderItem = useCallback(
    ({ item }: { item: ConnectionItem }) => (
      <ConnectionCard
        connection={item}
        onRequestUpgrade={handleRequestUpgrade}
        onAccept={handleAccept}
        onReject={handleReject}
        onMessage={handleMessage}
        isProcessing={processingId === item.id}
      />
    ),
    [
      handleRequestUpgrade,
      handleAccept,
      handleReject,
      handleMessage,
      processingId,
    ],
  );

  const renderEmpty = useCallback(() => {
    if (isLoading) return null;
    return <EmptyConnections filter={filter} />;
  }, [isLoading, filter]);

  const keyExtractor = useCallback((item: ConnectionItem) => item.id, []);

  // Incoming pending requests count
  const incomingCount = useMemo(
    () =>
      connections.filter(
        (c) => c.upgrade_requested_by_them && !c.upgrade_requested_by_me,
      ).length,
    [connections],
  );

  // Stats counts for filter
  const filterCounts = useMemo(
    () => ({
      all: total,
      STRANGER: strangersCount,
      SIGNAL: signalsCount,
      CONNECTED: connectedCount,
    }),
    [total, strangersCount, signalsCount, connectedCount],
  );

  // ========================================================
  // ERROR STATE
  // ========================================================

  if (error && connections.length === 0) {
    return (
      <SafeAreaView
        style={[styles.container, { backgroundColor: colors.background }]}
      >
        <View style={styles.errorContainer}>
          <Text style={styles.errorIcon}>⚠️</Text>
          <Text style={[styles.errorTitle, { color: colors.text }]}>
            Couldn't load connections
          </Text>
          <Text style={[styles.errorMessage, { color: colors.textSecondary }]}>
            {error}
          </Text>
          <TouchableOpacity
            onPress={() => {
              clearError();
              fetchConnections();
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
        {onBack && (
          <TouchableOpacity onPress={onBack} style={styles.backButton}>
            <Text style={[styles.backText, { color: colors.primary }]}>
              ← Back
            </Text>
          </TouchableOpacity>
        )}
        <View style={styles.headerRow}>
          <View>
            <Text style={[styles.headerTitle, { color: colors.text }]}>
              Connections
            </Text>
            <Text
              style={[styles.headerSubtitle, { color: colors.textSecondary }]}
            >
              Your people in the city
            </Text>
          </View>
          {incomingCount > 0 && (
            <View
              style={[styles.pendingBadge, { backgroundColor: colors.primary }]}
            >
              <Text style={styles.pendingBadgeText}>
                {incomingCount > 9 ? "9+" : incomingCount}
              </Text>
            </View>
          )}
        </View>
      </View>

      {/* Stats Bar */}
      <View style={[styles.statsBar, { backgroundColor: colors.surface }]}>
        <View style={styles.statItem}>
          <Text style={[styles.statNumber, { color: "#9CA3AF" }]}>
            {strangersCount}
          </Text>
          <Text style={[styles.statLabel, { color: colors.textSecondary }]}>
            Strangers
          </Text>
        </View>
        <View
          style={[styles.statDivider, { backgroundColor: colors.border }]}
        />
        <View style={styles.statItem}>
          <Text style={[styles.statNumber, { color: "#F59E0B" }]}>
            {signalsCount}
          </Text>
          <Text style={[styles.statLabel, { color: colors.textSecondary }]}>
            Signals
          </Text>
        </View>
        <View
          style={[styles.statDivider, { backgroundColor: colors.border }]}
        />
        <View style={styles.statItem}>
          <Text style={[styles.statNumber, { color: "#10B981" }]}>
            {connectedCount}
          </Text>
          <Text style={[styles.statLabel, { color: colors.textSecondary }]}>
            Connected
          </Text>
        </View>
      </View>

      {/* Filter */}
      <LevelFilter
        selected={filter}
        onSelect={handleFilterSelect}
        counts={filterCounts}
      />

      {/* Loading state (initial) */}
      {isLoading && connections.length === 0 ? (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={colors.primary} />
          <Text style={[styles.loadingText, { color: colors.textSecondary }]}>
            Loading connections...
          </Text>
        </View>
      ) : (
        <FlatList
          data={connections}
          renderItem={renderItem}
          keyExtractor={keyExtractor}
          contentContainerStyle={[
            styles.listContent,
            connections.length === 0 && styles.emptyListContent,
          ]}
          ListEmptyComponent={renderEmpty}
          refreshControl={
            <RefreshControl
              refreshing={isRefreshing}
              onRefresh={refresh}
              tintColor={colors.primary}
              colors={[colors.primary]}
            />
          }
          showsVerticalScrollIndicator={false}
          removeClippedSubviews={true}
          maxToRenderPerBatch={10}
          windowSize={10}
          initialNumToRender={10}
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
    paddingHorizontal: 16,
    paddingTop: 8,
    paddingBottom: 4,
  },
  backButton: {
    marginBottom: 8,
  },
  backText: {
    fontSize: 15,
    fontWeight: "500",
  },
  headerRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
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
  pendingBadge: {
    minWidth: 28,
    height: 28,
    borderRadius: 14,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 8,
  },
  pendingBadgeText: {
    color: "#FFFFFF",
    fontSize: 13,
    fontWeight: "700",
  },
  statsBar: {
    flexDirection: "row",
    marginHorizontal: 16,
    marginTop: 8,
    borderRadius: 12,
    paddingVertical: 12,
    paddingHorizontal: 4,
  },
  statItem: {
    flex: 1,
    alignItems: "center",
  },
  statNumber: {
    fontSize: 20,
    fontWeight: "700",
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
