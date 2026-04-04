// ===========================================
// LAYERS Profile Screen (Merged Version)
// ===========================================

import React, { useState, useEffect, useCallback } from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
  RefreshControl,
  ActivityIndicator,
  Alert,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useAuthStore } from "../../store/authStore";
import { Colors } from "../../constants/colors";
import { User } from "../../types";
import { profileService, ProfileStats } from "../../services/profile";
import { EditProfileModal, ProfileHeader, StatsGrid } from "../../components/profile";
import NotificationPreferencesScreen from "./NotificationPreferencesScreen";

// ============================================================
// MENU ITEMS
// ============================================================

interface MenuItem {
  key: string;
  icon: string;
  title: string;
  description: string;
  action: "navigate" | "toggle" | "danger";
}

const MENU_ITEMS: MenuItem[] = [
  {
    key: "edit",
    icon: "✏️",
    title: "Edit Profile",
    description: "Change username, bio, and avatar",
    action: "navigate",
  },
  {
    key: "notifications",
    icon: "🔔",
    title: "Notifications",
    description: "Push notification preferences",
    action: "navigate",
  },
  {
    key: "inventory",
    icon: "📦",
    title: "Inventory",
    description: "Saved artifacts and vouchers",
    action: "navigate",
  },
  {
    key: "achievements",
    icon: "🏆",
    title: "Achievements",
    description: "Badges and milestones",
    action: "navigate",
  },
  {
    key: "privacy",
    icon: "🔒",
    title: "Privacy & Safety",
    description: "Block list, data export",
    action: "navigate",
  },
  {
    key: "logout",
    icon: "🚪",
    title: "Log Out",
    description: "Sign out of LAYERS",
    action: "danger",
  },
];

// ============================================================
// SCREEN
// ============================================================

export default function ProfileScreen() {
  const { layer, user, logout, updateUser } = useAuthStore();
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];

  // State
  const [statsData, setStatsData] = useState<ProfileStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showNotificationPrefs, setShowNotificationPrefs] = useState(false);

  // ========================================================
  // LOAD DATA
  // ========================================================

  const loadProfileData = useCallback(async () => {
    try {
      const [profileRes, statsRes] = await Promise.allSettled([
        profileService.getProfile(),
        profileService.getStats(),
      ]);

      if (profileRes.status === "fulfilled") {
        updateUser(profileRes.value);
      }

      if (statsRes.status === "fulfilled") {
        setStatsData(statsRes.value);
      }
    } catch (error) {
      console.error("Failed to load profile data:", error);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [updateUser]);

  useEffect(() => {
    loadProfileData();
  }, [loadProfileData]);

  const handleRefresh = useCallback(() => {
    setIsRefreshing(true);
    loadProfileData();
  }, [loadProfileData]);

  // ========================================================
  // MENU HANDLERS
  // ========================================================

  const handleMenuPress = useCallback(
    (item: MenuItem) => {
      switch (item.key) {
        case "edit":
          setShowEditModal(true);
          break;
        case "notifications":
          setShowNotificationPrefs(true);
          break;
        case "inventory":
          Alert.alert("📦 Inventory", "Coming in Week 7!", [{ text: "OK" }]);
          break;
        case "achievements":
          Alert.alert("🏆 Achievements", "Coming in Week 7!", [{ text: "OK" }]);
          break;
        case "privacy":
          Alert.alert("🔒 Privacy", "Coming in Week 8!", [{ text: "OK" }]);
          break;
        case "logout":
          Alert.alert("Log Out", "Are you sure you want to log out?", [
            { text: "Cancel", style: "cancel" },
            {
              text: "Log Out",
              style: "destructive",
              onPress: async () => {
                try {
                  await logout();
                } catch (error) {
                  console.error("Logout failed:", error);
                }
              },
            },
          ]);
          break;
      }
    },
    [logout],
  );

  // ========================================================
  // PROFILE SAVED
  // ========================================================

  const handleProfileSaved = useCallback(
    (updatedUser: User) => {
      updateUser(updatedUser);
    },
    [updateUser],
  );

  // ========================================================
  // NOTIFICATION PREFS VIEW
  // ========================================================

  if (showNotificationPrefs) {
    return (
      <NotificationPreferencesScreen
        onBack={() => setShowNotificationPrefs(false)}
      />
    );
  }

  // ========================================================
  // LOADING STATE
  // ========================================================

  if (isLoading && !user) {
    return (
      <SafeAreaView
        style={[styles.container, { backgroundColor: colors.background }]}
      >
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={colors.primary} />
          <Text style={[styles.loadingText, { color: colors.textSecondary }]}>
            Loading profile...
          </Text>
        </View>
      </SafeAreaView>
    );
  }

  // ========================================================
  // MAIN RENDER
  // ========================================================

  const currentUser: User = user || {
    id: "",
    email: "",
    username: "anonymous",
    xp: 0,
    level: 1,
    reputation_score: 100,
    role: "USER" as const,
    is_active: true,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };

  return (
    <SafeAreaView
      style={[styles.container, { backgroundColor: colors.background }]}
      edges={["top"]}
    >
      <ScrollView
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl
            refreshing={isRefreshing}
            onRefresh={handleRefresh}
            tintColor={colors.primary}
            colors={[colors.primary]}
          />
        }
      >
        <ProfileHeader
          user={currentUser}
          onAvatarPress={() => setShowEditModal(true)}
          onEditPress={() => setShowEditModal(true)}
        />

        {/* Stats Grid */}
        {statsData && <StatsGrid stats={statsData} />}

        {/* Menu */}
        <View style={styles.menuContainer}>
          {MENU_ITEMS.map((item) => (
            <TouchableOpacity
              key={item.key}
              onPress={() => handleMenuPress(item)}
              style={[
                styles.menuItem,
                {
                  backgroundColor: colors.surface,
                  borderColor: colors.border || "transparent",
                },
                item.action === "danger" && styles.menuItemDanger,
              ]}
              activeOpacity={0.7}
            >
              <Text style={styles.menuIcon}>{item.icon}</Text>
              <View style={styles.menuContent}>
                <Text
                  style={[
                    styles.menuTitle,
                    {
                      color: item.action === "danger" ? "#EF4444" : colors.text,
                    },
                  ]}
                >
                  {item.title}
                </Text>
                <Text
                  style={[
                    styles.menuDescription,
                    { color: colors.textSecondary },
                  ]}
                >
                  {item.description}
                </Text>
              </View>
              {item.action !== "danger" && (
                <Text
                  style={[styles.menuChevron, { color: colors.textSecondary }]}
                >
                  ›
                </Text>
              )}
            </TouchableOpacity>
          ))}
        </View>

        {/* App version */}
        <Text style={[styles.version, { color: colors.textSecondary }]}>
          LAYERS v1.0.0 — Founded by @Kazyy
        </Text>
      </ScrollView>

      {/* Edit Profile Modal */}
      {showEditModal && (
        <EditProfileModal
          visible={showEditModal}
          onClose={() => setShowEditModal(false)}
          user={currentUser}
          onSaved={handleProfileSaved}
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
  loadingContainer: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  loadingText: {
    marginTop: 12,
    fontSize: 14,
  },
  menuContainer: {
    paddingHorizontal: 16,
    paddingTop: 8,
    gap: 8,
  },
  menuItem: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 14,
    paddingVertical: 14,
    borderRadius: 14,
    borderWidth: 1,
    gap: 12,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  menuItemDanger: {
    marginTop: 8,
  },
  menuIcon: {
    fontSize: 22,
    width: 32,
    textAlign: "center",
  },
  menuContent: {
    flex: 1,
  },
  menuTitle: {
    fontSize: 16,
    fontWeight: "600",
    marginBottom: 2,
  },
  menuDescription: {
    fontSize: 13,
    marginTop: 2,
  },
  menuChevron: {
    fontSize: 24,
    fontWeight: "300",
  },
  version: {
    textAlign: "center",
    fontSize: 12,
    paddingVertical: 32,
    marginBottom: 40,
  },
});
