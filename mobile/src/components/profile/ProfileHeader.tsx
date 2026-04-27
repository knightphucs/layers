/**
 * LAYERS — ProfileHeader Component
 * ==========================================
 * Displays avatar (initial or image), username, rank, bio.
 * Tap avatar to change photo (via parent callback).
 *
 * PATTERN: React.memo
 */

import React, { useMemo, useState, useEffect } from "react";
import { View, Text, TouchableOpacity, Image, StyleSheet } from "react-native";
import { Colors } from "../../constants/colors";
import { useAuthStore } from "../../store/authStore";
import { User } from "../../types";
import { getRankForLevel } from "../../services/profile";

interface ProfileHeaderProps {
  user: User;
  onAvatarPress?: () => void;
  onEditPress?: () => void;
}

const ProfileHeader = React.memo(
  ({ user, onAvatarPress, onEditPress }: ProfileHeaderProps) => {
    const layer = useAuthStore((s) => s.layer);
    const colors = Colors[layer.toLowerCase() as "light" | "shadow"];

    const rank = useMemo(() => getRankForLevel(user.level ?? 1), [user.level]);

    const initial = (user.username?.[0] ?? "?").toUpperCase();
    const hasAvatar = !!user.avatar_url;
    const [imageError, setImageError] = useState(false);
    useEffect(() => { setImageError(false); }, [user.avatar_url]);

    return (
      <View style={styles.container}>
        {/* Avatar */}
        <TouchableOpacity
          onPress={onAvatarPress}
          activeOpacity={0.8}
          style={styles.avatarWrapper}
        >
          {hasAvatar && !imageError ? (
            <Image
              source={{ uri: user.avatar_url! }}
              style={[styles.avatar, { borderColor: colors.primary }]}
              onError={() => {
                console.warn("[ProfileHeader] Avatar failed to load:", user.avatar_url);
                setImageError(true);
              }}
            />
          ) : (
            <View
              style={[
                styles.avatar,
                styles.avatarPlaceholder,
                {
                  backgroundColor: colors.primary,
                  borderColor: colors.primary,
                },
              ]}
            >
              <Text style={styles.avatarInitial}>{initial}</Text>
            </View>
          )}
          {/* Camera badge */}
          <View
            style={[
              styles.cameraBadge,
              { backgroundColor: colors.surface, borderColor: colors.border },
            ]}
          >
            <Text style={styles.cameraIcon}>📷</Text>
          </View>
        </TouchableOpacity>

        {/* Name + Rank */}
        <Text style={[styles.username, { color: colors.text }]}>
          @{user.username}
        </Text>

        <View style={styles.rankRow}>
          <Text style={styles.rankIcon}>{rank.icon}</Text>
          <Text style={[styles.rankTitle, { color: colors.primary }]}>
            {rank.title}
          </Text>
          <Text style={[styles.levelBadge, { color: colors.textSecondary }]}>
            Lv.{user.level ?? 1}
          </Text>
        </View>

        {/* Bio */}
        {user.bio ? (
          <Text style={[styles.bio, { color: colors.textSecondary }]}>
            {user.bio}
          </Text>
        ) : (
          <TouchableOpacity onPress={onEditPress}>
            <Text style={[styles.addBio, { color: colors.primary }]}>
              + Add a bio
            </Text>
          </TouchableOpacity>
        )}

        {/* Joined date */}
        <Text style={[styles.joined, { color: colors.textSecondary }]}>
          Joined{" "}
          {user.created_at
            ? new Date(user.created_at).toLocaleDateString("en-US", {
                month: "long",
                year: "numeric",
              })
            : "recently"}
        </Text>
      </View>
    );
  },
);

ProfileHeader.displayName = "ProfileHeader";

const styles = StyleSheet.create({
  container: {
    alignItems: "center",
    paddingTop: 16,
    paddingBottom: 20,
    paddingHorizontal: 20,
  },
  avatarWrapper: {
    position: "relative",
    marginBottom: 12,
  },
  avatar: {
    width: 90,
    height: 90,
    borderRadius: 45,
    borderWidth: 3,
  },
  avatarPlaceholder: {
    alignItems: "center",
    justifyContent: "center",
  },
  avatarInitial: {
    color: "#FFFFFF",
    fontSize: 36,
    fontWeight: "700",
  },
  cameraBadge: {
    position: "absolute",
    bottom: 0,
    right: -2,
    width: 30,
    height: 30,
    borderRadius: 15,
    borderWidth: 2,
    alignItems: "center",
    justifyContent: "center",
  },
  cameraIcon: {
    fontSize: 14,
  },
  username: {
    fontSize: 22,
    fontWeight: "700",
    marginBottom: 4,
  },
  rankRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    marginBottom: 10,
  },
  rankIcon: {
    fontSize: 16,
  },
  rankTitle: {
    fontSize: 14,
    fontWeight: "600",
  },
  levelBadge: {
    fontSize: 13,
    fontWeight: "500",
  },
  bio: {
    fontSize: 14,
    lineHeight: 20,
    textAlign: "center",
    maxWidth: 280,
    marginBottom: 6,
  },
  addBio: {
    fontSize: 14,
    fontWeight: "500",
    marginBottom: 6,
  },
  joined: {
    fontSize: 12,
  },
});

export default ProfileHeader;
