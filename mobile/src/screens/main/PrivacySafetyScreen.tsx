/**
 * LAYERS — PrivacySafetyScreen
 * ==========================================
 * Closes the "Coming in Week 8!" alert. Three sections:
 *
 *   1. BLOCKED USERS — list + unblock (GET/DELETE /users/.../block)
 *   2. YOUR DATA — what we store, in plain language
 *   3. DANGER ZONE — permanent account deletion (App Store requirement!)
 *      Flow: Delete button → warning → type password → POST /auth/me/delete
 *      → logout(). Deliberately slow — deletion should never be one tap.
 *
 * PATTERN: render-guard sub-screen with onBack prop (like ConnectionsScreen).
 */

import React, { useEffect, useState, useCallback } from "react";
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  TextInput,
  Modal,
  ActivityIndicator,
  Alert,
  StyleSheet,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { useAuthStore } from "../../store/authStore";
import { usersService, BlockedUser } from "../../services/users";
import { getErrorMessage } from "../../services";
import { Colors } from "../../constants/colors";

interface Props {
  onBack: () => void;
}

export default function PrivacySafetyScreen({ onBack }: Props) {
  const { layer, logout } = useAuthStore();
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];

  // Block list state
  const [blocks, setBlocks] = useState<BlockedUser[]>([]);
  const [isLoadingBlocks, setIsLoadingBlocks] = useState(true);

  // Delete account state
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deletePassword, setDeletePassword] = useState("");
  const [isDeleting, setIsDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  // ========================================================
  // BLOCK LIST
  // ========================================================

  const loadBlocks = useCallback(async () => {
    setIsLoadingBlocks(true);
    try {
      const data = await usersService.getBlocks();
      setBlocks(data.items);
    } catch (error) {
      console.error("Failed to load blocks:", error);
    } finally {
      setIsLoadingBlocks(false);
    }
  }, []);

  useEffect(() => {
    loadBlocks();
  }, [loadBlocks]);

  const handleUnblock = useCallback(
    (user: BlockedUser) => {
      Alert.alert(
        "Unblock user?",
        `${user.username} will be able to interact with you again.`,
        [
          { text: "Cancel", style: "cancel" },
          {
            text: "Unblock",
            onPress: async () => {
              try {
                await usersService.unblockUser(user.user_id);
                // Optimistic removal
                setBlocks((prev) =>
                  prev.filter((b) => b.user_id !== user.user_id),
                );
              } catch (error) {
                Alert.alert("Error", getErrorMessage(error));
              }
            },
          },
        ],
      );
    },
    [],
  );

  // ========================================================
  // DELETE ACCOUNT
  // ========================================================

  const handleDeleteConfirm = useCallback(async () => {
    if (deletePassword.length === 0) return;
    setIsDeleting(true);
    setDeleteError(null);
    try {
      await usersService.deleteAccount(deletePassword);
      // Account is gone — clear local session. No goodbye screen needed;
      // RootNavigator drops to Auth automatically.
      await logout();
    } catch (error) {
      setDeleteError(getErrorMessage(error));
      setIsDeleting(false);
    }
  }, [deletePassword, logout]);

  return (
    <SafeAreaView
      style={[styles.container, { backgroundColor: colors.background }]}
      edges={["top"]}
    >
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity
          onPress={onBack}
          hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}
          accessibilityRole="button"
          accessibilityLabel="Go back"
        >
          <Text style={[styles.backArrow, { color: colors.text }]}>←</Text>
        </TouchableOpacity>
        <Text style={[styles.headerTitle, { color: colors.text }]}>
          🔒 Privacy & Safety
        </Text>
        <View style={styles.headerSpacer} />
      </View>

      <ScrollView
        contentContainerStyle={styles.scroll}
        showsVerticalScrollIndicator={false}
      >
        {/* ============ BLOCKED USERS ============ */}
        <Text style={[styles.sectionTitle, { color: colors.text }]}>
          Blocked users
        </Text>
        <Text style={[styles.sectionDesc, { color: colors.textSecondary }]}>
          Blocked users can't reply to your letters, connect with you, or chat
          with you. They're never notified.
        </Text>

        {isLoadingBlocks ? (
          <ActivityIndicator
            size="small"
            color={colors.primary}
            style={styles.blockSpinner}
          />
        ) : blocks.length === 0 ? (
          <View
            style={[
              styles.emptyCard,
              { backgroundColor: colors.surface ?? colors.background },
            ]}
          >
            <Text style={[styles.emptyText, { color: colors.textSecondary }]}>
              🕊️ No blocked users. The city is peaceful.
            </Text>
          </View>
        ) : (
          blocks.map((user) => (
            <View
              key={user.user_id}
              style={[
                styles.blockRow,
                {
                  backgroundColor: colors.surface ?? colors.background,
                  borderColor: colors.border ?? "rgba(128,128,128,0.25)",
                },
              ]}
            >
              <Text style={styles.blockAvatar}>👤</Text>
              <View style={styles.blockInfo}>
                <Text style={[styles.blockName, { color: colors.text }]}>
                  {user.username}
                </Text>
                <Text
                  style={[styles.blockDate, { color: colors.textSecondary }]}
                >
                  Blocked{" "}
                  {new Date(user.blocked_at).toLocaleDateString("vi-VN")}
                </Text>
              </View>
              <TouchableOpacity
                style={[styles.unblockButton, { borderColor: colors.primary }]}
                onPress={() => handleUnblock(user)}
                accessibilityRole="button"
                accessibilityLabel={`Unblock ${user.username}`}
              >
                <Text style={[styles.unblockText, { color: colors.primary }]}>
                  Unblock
                </Text>
              </TouchableOpacity>
            </View>
          ))
        )}

        {/* ============ YOUR DATA ============ */}
        <Text style={[styles.sectionTitle, { color: colors.text }]}>
          Your data
        </Text>
        <View
          style={[
            styles.dataCard,
            { backgroundColor: colors.surface ?? colors.background },
          ]}
        >
          <Text style={[styles.dataText, { color: colors.textSecondary }]}>
            LAYERS stores your account info, the artifacts you create, and the
            map chunks you've explored. Your exact realtime location is never
            stored — only ~100m exploration chunks.{"\n\n"}
            Other users never see your precise position. Anonymous artifacts
            stay anonymous.
          </Text>
        </View>

        {/* ============ DANGER ZONE ============ */}
        <Text style={[styles.sectionTitle, { color: "#EF4444" }]}>
          Danger zone
        </Text>
        <TouchableOpacity
          style={styles.deleteButton}
          onPress={() => setShowDeleteModal(true)}
          accessibilityRole="button"
          accessibilityLabel="Delete account permanently"
        >
          <Text style={styles.deleteButtonText}>
            Delete my account permanently
          </Text>
        </TouchableOpacity>
        <Text style={[styles.deleteHint, { color: colors.textSecondary }]}>
          This erases your profile and removes your letters from the city.
          It cannot be undone.
        </Text>
      </ScrollView>

      {/* ============ DELETE CONFIRM MODAL ============ */}
      <Modal
        visible={showDeleteModal}
        transparent
        animationType="fade"
        onRequestClose={() => !isDeleting && setShowDeleteModal(false)}
      >
        <View style={styles.modalBackdrop}>
          <View
            style={[styles.modalCard, { backgroundColor: colors.background }]}
          >
            <Text style={styles.modalEmoji}>⚠️</Text>
            <Text style={[styles.modalTitle, { color: colors.text }]}>
              Delete your account?
            </Text>
            <Text style={[styles.modalBody, { color: colors.textSecondary }]}>
              Your profile, XP, badges, and streaks will be permanently erased.
              Your letters will be removed from the city.{"\n\n"}
              Enter your password to confirm:
            </Text>

            <TextInput
              style={[
                styles.modalInput,
                {
                  color: colors.text,
                  borderColor: colors.border ?? "rgba(128,128,128,0.4)",
                  backgroundColor: colors.surface ?? colors.background,
                },
              ]}
              placeholder="Current password"
              placeholderTextColor={colors.textSecondary}
              secureTextEntry
              value={deletePassword}
              onChangeText={setDeletePassword}
              editable={!isDeleting}
              accessibilityLabel="Password confirmation"
            />

            {deleteError && (
              <Text style={styles.modalError}>{deleteError}</Text>
            )}

            <TouchableOpacity
              style={[
                styles.modalDeleteButton,
                { opacity: deletePassword.length === 0 || isDeleting ? 0.5 : 1 },
              ]}
              onPress={handleDeleteConfirm}
              disabled={deletePassword.length === 0 || isDeleting}
              accessibilityRole="button"
              accessibilityLabel="Confirm permanent deletion"
            >
              {isDeleting ? (
                <ActivityIndicator size="small" color="#FFFFFF" />
              ) : (
                <Text style={styles.modalDeleteText}>
                  Delete forever
                </Text>
              )}
            </TouchableOpacity>

            <TouchableOpacity
              style={styles.modalCancel}
              onPress={() => {
                setShowDeleteModal(false);
                setDeletePassword("");
                setDeleteError(null);
              }}
              disabled={isDeleting}
              accessibilityRole="button"
              accessibilityLabel="Cancel deletion"
            >
              <Text
                style={[styles.modalCancelText, { color: colors.textSecondary }]}
              >
                Cancel
              </Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

// ============================================================
// STYLES
// ============================================================

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 20,
    paddingVertical: 12,
  },
  backArrow: { fontSize: 24, fontWeight: "600" },
  headerTitle: {
    flex: 1,
    fontSize: 20,
    fontWeight: "800",
    textAlign: "center",
  },
  headerSpacer: { width: 24 },
  scroll: { paddingHorizontal: 20, paddingBottom: 32 },
  sectionTitle: {
    fontSize: 16,
    fontWeight: "800",
    marginTop: 20,
    marginBottom: 6,
  },
  sectionDesc: { fontSize: 13, lineHeight: 19, marginBottom: 12 },
  blockSpinner: { marginVertical: 16 },
  emptyCard: { borderRadius: 14, padding: 18, alignItems: "center" },
  emptyText: { fontSize: 13 },
  blockRow: {
    flexDirection: "row",
    alignItems: "center",
    borderWidth: 1,
    borderRadius: 14,
    padding: 12,
    marginBottom: 8,
    gap: 10,
  },
  blockAvatar: { fontSize: 24 },
  blockInfo: { flex: 1 },
  blockName: { fontSize: 14, fontWeight: "700" },
  blockDate: { fontSize: 11, marginTop: 2 },
  unblockButton: {
    borderWidth: 1.5,
    borderRadius: 16,
    paddingHorizontal: 12,
    paddingVertical: 6,
  },
  unblockText: { fontSize: 12, fontWeight: "700" },
  dataCard: { borderRadius: 14, padding: 16 },
  dataText: { fontSize: 13, lineHeight: 20 },
  deleteButton: {
    backgroundColor: "#EF4444",
    borderRadius: 24,
    paddingVertical: 14,
    alignItems: "center",
    marginBottom: 8,
  },
  deleteButtonText: { color: "#FFFFFF", fontSize: 15, fontWeight: "700" },
  deleteHint: { fontSize: 12, lineHeight: 18, textAlign: "center" },
  modalBackdrop: {
    flex: 1,
    backgroundColor: "rgba(0,0,0,0.6)",
    justifyContent: "center",
    padding: 24,
  },
  modalCard: { borderRadius: 20, padding: 24, alignItems: "center" },
  modalEmoji: { fontSize: 44, marginBottom: 8 },
  modalTitle: { fontSize: 20, fontWeight: "800", marginBottom: 8 },
  modalBody: { fontSize: 14, lineHeight: 21, textAlign: "center" },
  modalInput: {
    alignSelf: "stretch",
    borderWidth: 1,
    borderRadius: 12,
    padding: 14,
    fontSize: 15,
    marginTop: 16,
  },
  modalError: {
    color: "#F87171",
    fontSize: 13,
    marginTop: 10,
    textAlign: "center",
  },
  modalDeleteButton: {
    alignSelf: "stretch",
    backgroundColor: "#EF4444",
    borderRadius: 22,
    paddingVertical: 14,
    alignItems: "center",
    marginTop: 16,
  },
  modalDeleteText: { color: "#FFFFFF", fontSize: 15, fontWeight: "800" },
  modalCancel: { marginTop: 12, padding: 8 },
  modalCancelText: { fontSize: 14, fontWeight: "600" },
});
