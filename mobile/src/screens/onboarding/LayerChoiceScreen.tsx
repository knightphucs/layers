/**
 * LAYERS — LayerChoiceScreen
 * ==========================================
 * The identity moment: pick your starting vibe.
 *
 *   ☀️ LIGHT  — healing, memories, slow connection
 *   🌙 SHADOW — mystery, legends, midnight challenges
 *
 * The choice applies the theme app-wide immediately (via
 * onboardingStore.chooseLayer → authStore.layer), and the user
 * can always flip later with the Layer Toggle on the map.
 */

import React, { useState, useCallback, useRef, useEffect } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  Animated,
  StyleSheet,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";

import { OnboardingStackParamList } from "../../types/onboarding";
import { Layer } from "../../types";
import { useOnboardingStore } from "../../store/onboardingStore";

type Props = {
  navigation: NativeStackNavigationProp<OnboardingStackParamList, "LayerChoice">;
};

// ============================================================
// LAYER CARD CONFIG
// ============================================================

const LAYER_CARDS: {
  layer: Layer;
  emoji: string;
  title: string;
  tagline: string;
  bullets: string[];
  background: string;
  border: string;
  text: string;
  textSecondary: string;
}[] = [
  {
    layer: "LIGHT",
    emoji: "☀️",
    title: "Light Layer",
    tagline: "The city that heals",
    bullets: ["Leave memories at places you love", "Slow Mail & Paper Planes", "Gentle, warm, romantic"],
    background: "#FFF7ED",
    border: "#F59E0B",
    text: "#1E293B",
    textSecondary: "#92400E",
  },
  {
    layer: "SHADOW",
    emoji: "🌙",
    title: "Shadow Layer",
    tagline: "The city after midnight",
    bullets: ["Glitch zones & urban legends", "Midnight-only secrets (23:00–03:00)", "Dark, thrilling, mysterious"],
    background: "#16121F",
    border: "#8B5CF6",
    text: "#E2E8F0",
    textSecondary: "#A78BFA",
  },
];

// ============================================================
// SCREEN
// ============================================================

export default function LayerChoiceScreen({ navigation }: Props) {
  const { chooseLayer } = useOnboardingStore();
  const [selected, setSelected] = useState<Layer | null>(null);

  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.timing(fadeAnim, {
      toValue: 1,
      duration: 500,
      useNativeDriver: true,
    }).start();
  }, [fadeAnim]);

  const handleSelect = useCallback((layer: Layer) => {
    setSelected(layer);
  }, []);

  const handleContinue = useCallback(() => {
    if (!selected) return;
    chooseLayer(selected); // applies theme app-wide immediately
    navigation.navigate("Permissions");
  }, [selected, chooseLayer, navigation]);

  // Screen bg follows selection (defaults to neutral dark)
  const screenBg =
    selected === "LIGHT" ? "#F0F4FF" : selected === "SHADOW" ? "#0F0F1A" : "#101423";
  const headerColor = selected === "LIGHT" ? "#1E293B" : "#F1F5F9";
  const subColor = selected === "LIGHT" ? "#64748B" : "#94A3B8";

  return (
    <View style={[styles.container, { backgroundColor: screenBg }]}>
      <SafeAreaView style={styles.safeArea} edges={["top", "bottom"]}>
        <Animated.View style={[styles.content, { opacity: fadeAnim }]}>
          <Text style={[styles.header, { color: headerColor }]}>
            Choose your layer
          </Text>
          <Text style={[styles.subHeader, { color: subColor }]}>
            This sets your starting vibe. You can flip anytime with the toggle
            on the map.
          </Text>

          {LAYER_CARDS.map((card) => {
            const isSelected = selected === card.layer;
            return (
              <TouchableOpacity
                key={card.layer}
                style={[
                  styles.card,
                  {
                    backgroundColor: card.background,
                    borderColor: isSelected ? card.border : "transparent",
                    borderWidth: isSelected ? 3 : 1,
                    transform: [{ scale: isSelected ? 1.02 : 1 }],
                  },
                ]}
                onPress={() => handleSelect(card.layer)}
                activeOpacity={0.85}
                accessibilityRole="button"
                accessibilityLabel={`Choose ${card.title}`}
                accessibilityState={{ selected: isSelected }}
              >
                <View style={styles.cardHeader}>
                  <Text style={styles.cardEmoji}>{card.emoji}</Text>
                  <View style={styles.cardTitleBlock}>
                    <Text style={[styles.cardTitle, { color: card.text }]}>
                      {card.title}
                    </Text>
                    <Text style={[styles.cardTagline, { color: card.textSecondary }]}>
                      {card.tagline}
                    </Text>
                  </View>
                  {isSelected && <Text style={styles.checkmark}>✓</Text>}
                </View>
                {card.bullets.map((bullet, i) => (
                  <Text
                    key={i}
                    style={[styles.bullet, { color: card.textSecondary }]}
                  >
                    ·  {bullet}
                  </Text>
                ))}
              </TouchableOpacity>
            );
          })}
        </Animated.View>

        {/* Continue */}
        <View style={styles.footer}>
          <TouchableOpacity
            style={[
              styles.continueButton,
              {
                backgroundColor: selected
                  ? selected === "LIGHT"
                    ? "#F59E0B"
                    : "#8B5CF6"
                  : "#475569",
                opacity: selected ? 1 : 0.5,
              },
            ]}
            onPress={handleContinue}
            disabled={!selected}
            accessibilityRole="button"
            accessibilityLabel="Continue"
          >
            <Text style={styles.continueText}>
              {selected ? "Continue →" : "Pick a layer to continue"}
            </Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    </View>
  );
}

// ============================================================
// STYLES
// ============================================================

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  safeArea: {
    flex: 1,
  },
  content: {
    flex: 1,
    paddingHorizontal: 24,
    paddingTop: 24,
  },
  header: {
    fontSize: 26,
    fontWeight: "800",
    marginBottom: 8,
  },
  subHeader: {
    fontSize: 14,
    lineHeight: 20,
    marginBottom: 24,
  },
  card: {
    borderRadius: 20,
    padding: 20,
    marginBottom: 16,
  },
  cardHeader: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 12,
    gap: 12,
  },
  cardEmoji: {
    fontSize: 36,
  },
  cardTitleBlock: {
    flex: 1,
  },
  cardTitle: {
    fontSize: 20,
    fontWeight: "800",
  },
  cardTagline: {
    fontSize: 13,
    marginTop: 2,
  },
  checkmark: {
    fontSize: 22,
    fontWeight: "800",
    color: "#34D399",
  },
  bullet: {
    fontSize: 13,
    lineHeight: 22,
  },
  footer: {
    paddingHorizontal: 24,
    paddingBottom: 16,
  },
  continueButton: {
    borderRadius: 28,
    paddingVertical: 16,
    alignItems: "center",
  },
  continueText: {
    color: "#FFFFFF",
    fontSize: 16,
    fontWeight: "700",
  },
});
