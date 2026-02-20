/**
 * LAYERS - App Entry Point (Day 5 - Polished)
 *
 * NEW IN DAY 5:
 * - ToastProvider for non-intrusive notifications
 * - OfflineBanner for network status
 * - StatusBar theming based on Light/Shadow layer
 * - Error boundary wrapper
 */

import React from "react";
import { StatusBar, View, Text, StyleSheet } from "react-native";
import { NavigationContainer } from "@react-navigation/native";
import { GestureHandlerRootView } from "react-native-gesture-handler";
import { SafeAreaProvider } from "react-native-safe-area-context";

// Navigation
import RootNavigator from "./src/navigation/RootNavigator";

// Polish components
import { ToastProvider } from "./src/components/Toast";
import OfflineBanner from "./src/components/OfflineBanner";

// Store
import { useAuthStore } from "./src/store/authStore";

// ============================================================
// ERROR BOUNDARY - Catches crashes, shows friendly message
// ============================================================

class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean; error: Error | null }
> {
  constructor(props: any) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: any) {
    // Log to error reporting service in production
    console.error("[LAYERS CRASH]", error, errorInfo);
    // TODO: Sentry.captureException(error);
  }

  render() {
    if (this.state.hasError) {
      return (
        <View style={crashStyles.container}>
          <Text style={crashStyles.emoji}>🌆</Text>
          <Text style={crashStyles.title}>Oops! Something went wrong</Text>
          <Text style={crashStyles.message}>
            LAYERS hit an unexpected error. Please restart the app.
          </Text>
          <Text style={crashStyles.detail}>
            {__DEV__ ? this.state.error?.message : "Error ID: " + Date.now()}
          </Text>
        </View>
      );
    }
    return this.props.children;
  }
}

const crashStyles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: "center",
    alignItems: "center",
    backgroundColor: "#0F0F1A",
    padding: 32,
  },
  emoji: { fontSize: 64, marginBottom: 24 },
  title: {
    fontSize: 22,
    fontWeight: "700",
    color: "#E2E8F0",
    marginBottom: 12,
  },
  message: {
    fontSize: 15,
    color: "#94A3B8",
    textAlign: "center",
    lineHeight: 24,
  },
  detail: {
    fontSize: 11,
    color: "#4A5568",
    marginTop: 24,
    fontFamily: Platform.OS === "ios" ? "Menlo" : "monospace",
  },
});

// ============================================================
// STATUS BAR - Changes based on Light/Shadow layer
// ============================================================

function DynamicStatusBar() {
  const layer = useAuthStore((state) => state.layer);
  const isShadowMode = layer === "SHADOW";
  return (
    <StatusBar
      barStyle={isShadowMode ? "light-content" : "dark-content"}
      backgroundColor={isShadowMode ? "#0F0F1A" : "#F0F4FF"}
      animated
    />
  );
}

// ============================================================
// APP - Main entry point with all providers
// ============================================================

// Need to import Platform for crash screen font
import { Platform } from "react-native";

export default function App() {
  return (
    <ErrorBoundary>
      <GestureHandlerRootView style={{ flex: 1 }}>
        <SafeAreaProvider>
          <ToastProvider>
            <NavigationContainer>
              <DynamicStatusBar />
              <OfflineBanner />
              <RootNavigator />
            </NavigationContainer>
          </ToastProvider>
        </SafeAreaProvider>
      </GestureHandlerRootView>
    </ErrorBoundary>
  );
}
