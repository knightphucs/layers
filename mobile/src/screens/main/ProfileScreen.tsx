// ===========================================
// LAYERS Profile Screen (Placeholder)
// ===========================================

import React from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  ScrollView,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useAuthStore } from "../../store/authStore";
import { Colors } from "../../constants/colors";

export default function ProfileScreen() {
  const { layer, user, logout } = useAuthStore();
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];

  const stats = [
    { label: "XP", value: user?.xp || 0, emoji: "⭐" },
    { label: "Level", value: user?.level || 1, emoji: "🎮" },
    { label: "Rep", value: user?.reputation_score || 100, emoji: "💎" },
  ];

  const menuItems = [
    { emoji: "📦", title: "Inventory", desc: "Your saved items" },
    { emoji: "🏆", title: "Achievements", desc: "Badges & rewards" },
    { emoji: "📊", title: "Statistics", desc: "Your journey" },
    { emoji: "⚙️", title: "Settings", desc: "App preferences" },
  ];

  return (
    <SafeAreaView
      style={[styles.container, { backgroundColor: colors.background }]}
    >
      <ScrollView showsVerticalScrollIndicator={false}>
        {/* Profile Header */}
        <View style={styles.header}>
          <View style={[styles.avatar, { backgroundColor: colors.primary }]}>
            <Text style={styles.avatarText}>
              {user?.username?.[0]?.toUpperCase() || "?"}
            </Text>
          </View>
          <Text style={[styles.username, { color: colors.text }]}>
            @{user?.username || "anonymous"}
          </Text>
          <Text style={[styles.email, { color: colors.textSecondary }]}>
            {user?.email || "No email"}
          </Text>
        </View>

        {/* Stats */}
        <View style={styles.statsRow}>
          {stats.map((stat, index) => (
            <View
              key={index}
              style={[styles.statCard, { backgroundColor: colors.surface }]}
            >
              <Text style={styles.statEmoji}>{stat.emoji}</Text>
              <Text style={[styles.statValue, { color: colors.text }]}>
                {stat.value}
              </Text>
              <Text style={[styles.statLabel, { color: colors.textSecondary }]}>
                {stat.label}
              </Text>
            </View>
          ))}
        </View>

        {/* Menu */}
        <View style={styles.menu}>
          {menuItems.map((item, index) => (
            <TouchableOpacity
              key={index}
              style={[styles.menuItem, { backgroundColor: colors.surface }]}
            >
              <Text style={styles.menuEmoji}>{item.emoji}</Text>
              <View style={styles.menuContent}>
                <Text style={[styles.menuTitle, { color: colors.text }]}>
                  {item.title}
                </Text>
                <Text
                  style={[styles.menuDesc, { color: colors.textSecondary }]}
                >
                  {item.desc}
                </Text>
              </View>
              <Text style={[styles.menuArrow, { color: colors.textSecondary }]}>
                →
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* Logout */}
        <TouchableOpacity style={styles.logoutButton} onPress={logout}>
          <Text style={styles.logoutText}>🚪 Sign Out</Text>
        </TouchableOpacity>

        <Text style={[styles.version, { color: colors.textSecondary }]}>
          LAYERS v0.1.0 (Week 2 Dev Build)
        </Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    alignItems: "center",
    paddingTop: 24,
    paddingBottom: 24,
  },
  avatar: {
    width: 100,
    height: 100,
    borderRadius: 50,
    justifyContent: "center",
    alignItems: "center",
    marginBottom: 16,
  },
  avatarText: {
    fontSize: 40,
    fontWeight: "bold",
    color: "#FFFFFF",
  },
  username: {
    fontSize: 24,
    fontWeight: "bold",
    marginBottom: 4,
  },
  email: {
    fontSize: 14,
  },
  statsRow: {
    flexDirection: "row",
    paddingHorizontal: 24,
    gap: 12,
  },
  statCard: {
    flex: 1,
    alignItems: "center",
    paddingVertical: 16,
    borderRadius: 16,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  statEmoji: {
    fontSize: 24,
    marginBottom: 8,
  },
  statValue: {
    fontSize: 24,
    fontWeight: "bold",
  },
  statLabel: {
    fontSize: 12,
    marginTop: 4,
  },
  menu: {
    paddingHorizontal: 24,
    paddingTop: 24,
    gap: 12,
  },
  menuItem: {
    flexDirection: "row",
    alignItems: "center",
    padding: 16,
    borderRadius: 16,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  menuEmoji: {
    fontSize: 24,
    marginRight: 16,
  },
  menuContent: {
    flex: 1,
  },
  menuTitle: {
    fontSize: 16,
    fontWeight: "600",
    marginBottom: 2,
  },
  menuDesc: {
    fontSize: 13,
  },
  menuArrow: {
    fontSize: 18,
  },
  logoutButton: {
    marginHorizontal: 24,
    marginTop: 32,
    padding: 16,
    backgroundColor: Colors.light.error + "15",
    borderRadius: 12,
    alignItems: "center",
  },
  logoutText: {
    color: Colors.light.error,
    fontSize: 16,
    fontWeight: "600",
  },
  version: {
    textAlign: "center",
    marginTop: 24,
    marginBottom: 100,
    fontSize: 12,
  },
});
