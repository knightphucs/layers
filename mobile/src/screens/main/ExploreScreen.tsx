// ===========================================
// LAYERS Explore Screen (Placeholder)
// ===========================================

import React from "react";
import { View, Text, StyleSheet, ScrollView } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useAuthStore } from "../../store/authStore";
import { Colors } from "../../constants/colors";

export default function ExploreScreen() {
  const { layer } = useAuthStore();
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];

  const features = [
    {
      emoji: "💌",
      title: "Memory Inbox",
      desc: "Discover letters and memories",
    },
    {
      emoji: "✈️",
      title: "Paper Planes",
      desc: "Send messages to random places",
    },
    { emoji: "⏰", title: "Time Capsules", desc: "Messages from the future" },
    { emoji: "🎁", title: "Voucher Hunt", desc: "Find hidden rewards" },
    { emoji: "🔥", title: "Campfire Chat", desc: "Talk with nearby users" },
    { emoji: "🗺️", title: "Fog of War", desc: "Explore to reveal the map" },
  ];

  return (
    <SafeAreaView
      style={[styles.container, { backgroundColor: colors.background }]}
    >
      <Text style={[styles.title, { color: colors.text }]}>Explore</Text>
      <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
        Discover what's around you
      </Text>

      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        {features.map((feature, index) => (
          <View
            key={index}
            style={[styles.card, { backgroundColor: colors.surface }]}
          >
            <Text style={styles.cardEmoji}>{feature.emoji}</Text>
            <View style={styles.cardContent}>
              <Text style={[styles.cardTitle, { color: colors.text }]}>
                {feature.title}
              </Text>
              <Text style={[styles.cardDesc, { color: colors.textSecondary }]}>
                {feature.desc}
              </Text>
            </View>
            <Text style={[styles.cardArrow, { color: colors.textSecondary }]}>
              →
            </Text>
          </View>
        ))}

        <View style={styles.comingSoon}>
          <Text
            style={[styles.comingSoonText, { color: colors.textSecondary }]}
          >
            🚧 Full explore features coming in Week 4-6!
          </Text>
        </View>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  title: {
    fontSize: 32,
    fontWeight: "bold",
    paddingHorizontal: 24,
    paddingTop: 16,
  },
  subtitle: {
    fontSize: 16,
    paddingHorizontal: 24,
    marginBottom: 24,
  },
  scroll: {
    flex: 1,
  },
  scrollContent: {
    paddingHorizontal: 24,
    paddingBottom: 100,
  },
  card: {
    flexDirection: "row",
    alignItems: "center",
    padding: 20,
    borderRadius: 16,
    marginBottom: 12,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.05,
    shadowRadius: 8,
    elevation: 2,
  },
  cardEmoji: {
    fontSize: 32,
    marginRight: 16,
  },
  cardContent: {
    flex: 1,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: "600",
    marginBottom: 4,
  },
  cardDesc: {
    fontSize: 14,
  },
  cardArrow: {
    fontSize: 20,
  },
  comingSoon: {
    marginTop: 24,
    padding: 16,
    alignItems: "center",
  },
  comingSoonText: {
    fontSize: 14,
    textAlign: "center",
  },
});
