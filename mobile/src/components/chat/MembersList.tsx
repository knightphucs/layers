/**
 * LAYERS — MembersList Component
 * ===============================================
 * Horizontal scrollable row of campfire member avatars.
 *
 * - Anonymous mode: members without avatar_url show initials
 * - Online indicator: green dot on bottom-right of avatar
 * - Online members sorted first
 *
 * PATTERN: React.memo. Uses Colors[layer] theming.
 */

import React, { useMemo } from "react";
import { View, Text, Image, ScrollView, StyleSheet } from "react-native";
import { Colors } from "../../constants/colors";
import { useAuthStore } from "../../store/authStore";
import { CampfireMemberInfo } from "../../types/chat";

// ============================================================
// SINGLE AVATAR
// ============================================================

interface MemberAvatarProps {
  member: CampfireMemberInfo;
  isMe: boolean;
}

const MemberAvatar = React.memo(function MemberAvatar({
  member,
  isMe,
}: MemberAvatarProps) {
  const layer = useAuthStore((s) => s.layer);
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];

  // Anonymous fallback — first letter of username, or "?" for true anon
  const displayName = member.username || "Anonymous";
  const initial = (member.username?.[0] || "?").toUpperCase();

  return (
    <View style={styles.avatarWrap}>
      <View style={styles.avatarContainer}>
        {member.avatar_url ? (
          <Image source={{ uri: member.avatar_url }} style={styles.avatar} />
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

        {/* Online dot */}
        {member.is_online && (
          <View style={[styles.onlineDot, { borderColor: colors.surface }]} />
        )}
      </View>

      <Text
        style={[styles.name, { color: colors.textSecondary }]}
        numberOfLines={1}
      >
        {isMe ? "You" : displayName}
      </Text>
    </View>
  );
});

// ============================================================
// LIST
// ============================================================

interface MembersListProps {
  members: CampfireMemberInfo[];
}

function MembersListComponent({ members }: MembersListProps) {
  const layer = useAuthStore((s) => s.layer);
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];
  const currentUserId = useAuthStore((s) => s.user?.id);

  // Online members first, then by join time
  const sorted = useMemo(() => {
    return [...members].sort((a, b) => {
      if (a.is_online !== b.is_online) return a.is_online ? -1 : 1;
      return a.joined_at < b.joined_at ? -1 : 1;
    });
  }, [members]);

  if (members.length === 0) {
    return null;
  }

  return (
    <View
      style={[
        styles.container,
        {
          backgroundColor: colors.background,
          borderBottomColor: colors.border,
        },
      ]}
    >
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.scrollContent}
      >
        {sorted.map((member) => (
          <MemberAvatar
            key={member.user_id}
            member={member}
            isMe={member.user_id === currentUserId}
          />
        ))}
      </ScrollView>
    </View>
  );
}

export const MembersList = React.memo(MembersListComponent);
MembersList.displayName = "MembersList";

// ============================================================
// STYLES
// ============================================================

const styles = StyleSheet.create({
  container: {
    borderBottomWidth: 1,
    paddingVertical: 8,
  },
  scrollContent: {
    paddingHorizontal: 12,
    gap: 14,
  },
  avatarWrap: {
    alignItems: "center",
    width: 52,
  },
  avatarContainer: {
    position: "relative",
  },
  avatar: {
    width: 44,
    height: 44,
    borderRadius: 22,
  },
  avatarPlaceholder: {
    width: 44,
    height: 44,
    borderRadius: 22,
    alignItems: "center",
    justifyContent: "center",
  },
  avatarInitial: {
    fontSize: 18,
    fontWeight: "600",
  },
  onlineDot: {
    position: "absolute",
    bottom: 0,
    right: 0,
    width: 12,
    height: 12,
    borderRadius: 6,
    backgroundColor: "#10B981",
    borderWidth: 2,
  },
  name: {
    fontSize: 11,
    marginTop: 4,
    textAlign: "center",
  },
});

export default MembersList;
