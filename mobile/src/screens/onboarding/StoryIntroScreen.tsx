/**
 * LAYERS — StoryIntroScreen
 * ==========================================
 * The story-mode opening: 4 swipeable pages telling the LAYERS
 * philosophy ("The city isn't flat") before any UI chrome appears.
 *
 * DESIGN NOTES:
 *   - Each page previews its theme: neutral / light / shadow backgrounds,
 *     so the user *feels* the dual-layer concept before choosing one.
 *   - Emoji "hero" pulses gently — same motion language as ArtifactMarker.
 *   - Skip is always available (respect the user's time).
 */

import React, { useRef, useState, useCallback, useEffect } from "react";
import {
  View,
  Text,
  FlatList,
  Animated,
  Dimensions,
  TouchableOpacity,
  StyleSheet,
  ViewToken,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";

import { OnboardingStackParamList, STORY_PAGES, StoryPage } from "../../types/onboarding";
import { ProgressDots } from "../../components/onboarding";

const { width: SCREEN_WIDTH } = Dimensions.get("window");

type Props = {
  navigation: NativeStackNavigationProp<OnboardingStackParamList, "StoryIntro">;
};

// ============================================================
// PER-THEME PALETTES (page-local, previews Light/Shadow identity)
// ============================================================

const PAGE_THEMES = {
  neutral: {
    background: "#101423",
    text: "#F1F5F9",
    textSecondary: "#94A3B8",
    accent: "#818CF8",
  },
  light: {
    background: "#F0F4FF",
    text: "#1E293B",
    textSecondary: "#64748B",
    accent: "#F59E0B",
  },
  shadow: {
    background: "#0F0F1A",
    text: "#E2E8F0",
    textSecondary: "#94A3B8",
    accent: "#8B5CF6",
  },
} as const;

// ============================================================
// STORY PAGE ITEM
// ============================================================

const StoryPageItem = React.memo(function StoryPageItem({
  page,
}: {
  page: StoryPage;
}) {
  const theme = PAGE_THEMES[page.theme];
  const pulseAnim = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    const pulse = Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, {
          toValue: 1.08,
          duration: 1200,
          useNativeDriver: true,
        }),
        Animated.timing(pulseAnim, {
          toValue: 1,
          duration: 1200,
          useNativeDriver: true,
        }),
      ]),
    );
    pulse.start();
    return () => pulse.stop();
  }, [pulseAnim]);

  return (
    <View style={[styles.page, { backgroundColor: theme.background }]}>
      <Animated.Text
        style={[styles.pageEmoji, { transform: [{ scale: pulseAnim }] }]}
      >
        {page.emoji}
      </Animated.Text>
      <Text style={[styles.pageTitle, { color: theme.text }]}>
        {page.title}
      </Text>
      <View style={[styles.accentBar, { backgroundColor: theme.accent }]} />
      <Text style={[styles.pageBody, { color: theme.textSecondary }]}>
        {page.body}
      </Text>
    </View>
  );
});

// ============================================================
// SCREEN
// ============================================================

export default function StoryIntroScreen({ navigation }: Props) {
  const listRef = useRef<FlatList<StoryPage>>(null);
  const [activeIndex, setActiveIndex] = useState(0);

  const activeTheme = PAGE_THEMES[STORY_PAGES[activeIndex].theme];
  const isLastPage = activeIndex === STORY_PAGES.length - 1;

  // Track visible page
  const onViewableItemsChanged = useRef(
    ({ viewableItems }: { viewableItems: ViewToken[] }) => {
      if (viewableItems.length > 0 && viewableItems[0].index != null) {
        setActiveIndex(viewableItems[0].index);
      }
    },
  ).current;

  const viewabilityConfig = useRef({ itemVisiblePercentThreshold: 60 }).current;

  const handleNext = useCallback(() => {
    if (isLastPage) {
      navigation.navigate("LayerChoice");
    } else {
      listRef.current?.scrollToIndex({
        index: activeIndex + 1,
        animated: true,
      });
    }
  }, [isLastPage, activeIndex, navigation]);

  const handleSkip = useCallback(() => {
    navigation.navigate("LayerChoice");
  }, [navigation]);

  const renderItem = useCallback(
    ({ item }: { item: StoryPage }) => <StoryPageItem page={item} />,
    [],
  );

  return (
    <View style={[styles.container, { backgroundColor: activeTheme.background }]}>
      <SafeAreaView style={styles.safeArea} edges={["top", "bottom"]}>
        {/* Skip */}
        <View style={styles.topBar}>
          <TouchableOpacity
            onPress={handleSkip}
            hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}
            accessibilityRole="button"
            accessibilityLabel="Skip intro"
          >
            <Text style={[styles.skipText, { color: activeTheme.textSecondary }]}>
              Skip
            </Text>
          </TouchableOpacity>
        </View>

        {/* Story pager */}
        <FlatList
          ref={listRef}
          data={STORY_PAGES}
          keyExtractor={(item) => item.key}
          renderItem={renderItem}
          horizontal
          pagingEnabled
          showsHorizontalScrollIndicator={false}
          onViewableItemsChanged={onViewableItemsChanged}
          viewabilityConfig={viewabilityConfig}
          getItemLayout={(_, index) => ({
            length: SCREEN_WIDTH,
            offset: SCREEN_WIDTH * index,
            index,
          })}
        />

        {/* Footer: dots + next */}
        <View style={styles.footer}>
          <ProgressDots
            count={STORY_PAGES.length}
            activeIndex={activeIndex}
            color={activeTheme.accent}
            inactiveColor={activeTheme.textSecondary}
          />
          <TouchableOpacity
            style={[styles.nextButton, { backgroundColor: activeTheme.accent }]}
            onPress={handleNext}
            accessibilityRole="button"
            accessibilityLabel={isLastPage ? "Choose your layer" : "Next page"}
          >
            <Text style={styles.nextText}>
              {isLastPage ? "Choose your layer →" : "Next"}
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
  topBar: {
    flexDirection: "row",
    justifyContent: "flex-end",
    paddingHorizontal: 24,
    paddingTop: 8,
  },
  skipText: {
    fontSize: 14,
    fontWeight: "600",
  },
  page: {
    width: SCREEN_WIDTH,
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    paddingHorizontal: 40,
  },
  pageEmoji: {
    fontSize: 88,
    marginBottom: 28,
  },
  pageTitle: {
    fontSize: 28,
    fontWeight: "800",
    textAlign: "center",
    marginBottom: 16,
    letterSpacing: 0.5,
  },
  accentBar: {
    width: 48,
    height: 4,
    borderRadius: 2,
    marginBottom: 20,
  },
  pageBody: {
    fontSize: 16,
    lineHeight: 26,
    textAlign: "center",
  },
  footer: {
    paddingHorizontal: 24,
    paddingBottom: 16,
    gap: 20,
  },
  nextButton: {
    borderRadius: 28,
    paddingVertical: 16,
    alignItems: "center",
  },
  nextText: {
    color: "#FFFFFF",
    fontSize: 16,
    fontWeight: "700",
  },
});
