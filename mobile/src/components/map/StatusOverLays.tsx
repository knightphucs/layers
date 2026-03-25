/**
 * LAYERS - Offline Banner & Error Boundary
 * ====================================
 * Two essential UI components for production quality:
 *
 * 1. OfflineBanner — slides down when network drops
 *    - Yellow/orange warning bar
 *    - "No internet — showing cached data"
 *    - Auto-hides when connection restored
 *
 * 2. MapErrorBoundary — catches React crashes
 *    - Wraps MapScreen children
 *    - Shows friendly fallback instead of white screen
 *    - "Retry" button to remount
 *
 * 3. GPSAccuracyIndicator — shows GPS signal quality
 *    - Green: <15m accuracy (great)
 *    - Yellow: 15-50m (okay)
 *    - Red: >50m (poor, may affect unlocking)
 */

import React, {
  useEffect,
  useRef,
  useState,
  Component,
  ReactNode,
} from "react";
import {
  View,
  Text,
  StyleSheet,
  Animated,
  TouchableOpacity,
  Platform,
} from "react-native";
import NetInfo from "@react-native-community/netinfo";

// ============================================================
// OFFLINE BANNER
// ============================================================

interface OfflineBannerProps {
  isShadow: boolean;
}

export function OfflineBanner({ isShadow }: OfflineBannerProps) {
  const [isOffline, setIsOffline] = useState(false);
  const slideAnim = useRef(new Animated.Value(-50)).current;

  useEffect(() => {
    const unsubscribe = NetInfo.addEventListener((state) => {
      const offline = !(
        state.isConnected && state.isInternetReachable !== false
      );
      setIsOffline(offline);

      Animated.spring(slideAnim, {
        toValue: offline ? 0 : -50,
        friction: 8,
        useNativeDriver: true,
      }).start();
    });

    return () => unsubscribe();
  }, []);

  if (!isOffline) return null;

  return (
    <Animated.View
      style={[
        styles.offlineBanner,
        {
          backgroundColor: isShadow ? "#92400E" : "#F59E0B",
          transform: [{ translateY: slideAnim }],
        },
      ]}
    >
      <Text style={styles.offlineText}>
        📡 No internet — map data may be outdated
      </Text>
    </Animated.View>
  );
}

// ============================================================
// GPS ACCURACY INDICATOR
// ============================================================

interface GPSAccuracyProps {
  accuracy: number | null; // meters
  isShadow: boolean;
}

export function GPSAccuracyIndicator({ accuracy, isShadow }: GPSAccuracyProps) {
  if (accuracy === null) return null;

  let color: string;
  let label: string;

  if (accuracy <= 15) {
    color = "#10B981"; // Green
    label = "GPS ●";
  } else if (accuracy <= 50) {
    color = "#F59E0B"; // Yellow
    label = "GPS ◐";
  } else {
    color = "#EF4444"; // Red
    label = "GPS ○";
  }

  return (
    <View
      style={[
        styles.gpsIndicator,
        { backgroundColor: isShadow ? "#1F2937" : "#F9FAFB" },
      ]}
    >
      <View style={[styles.gpsDot, { backgroundColor: color }]} />
      <Text style={[styles.gpsText, { color }]}>{label}</Text>
      <Text
        style={[
          styles.gpsAccuracy,
          { color: isShadow ? "#9CA3AF" : "#6B7280" },
        ]}
      >
        ±{Math.round(accuracy)}m
      </Text>
    </View>
  );
}

// ============================================================
// ERROR BOUNDARY (Class component — React requirement)
// ============================================================

interface ErrorBoundaryProps {
  children: ReactNode;
  isShadow: boolean;
  onRetry?: () => void;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

export class MapErrorBoundary extends Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error("[MapErrorBoundary] Caught:", error, errorInfo);
    // TODO Week 7: Send to Sentry/Crashlytics
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null });
    this.props.onRetry?.();
  };

  render() {
    if (this.state.hasError) {
      const { isShadow } = this.props;
      return (
        <View
          style={[
            styles.errorContainer,
            {
              backgroundColor: isShadow ? "#1A1025" : "#FFF",
            },
          ]}
        >
          <Text style={styles.errorEmoji}>🗺️</Text>
          <Text
            style={[
              styles.errorTitle,
              {
                color: isShadow ? "#F3F4F6" : "#1F2937",
              },
            ]}
          >
            Map hit a snag
          </Text>
          <Text
            style={[
              styles.errorMessage,
              {
                color: isShadow ? "#9CA3AF" : "#6B7280",
              },
            ]}
          >
            Something went wrong rendering the map. This is usually temporary.
          </Text>
          <TouchableOpacity
            style={[
              styles.retryBtn,
              {
                backgroundColor: isShadow ? "#8B5CF6" : "#3B82F6",
              },
            ]}
            onPress={this.handleRetry}
          >
            <Text style={styles.retryText}>🔄 Try Again</Text>
          </TouchableOpacity>
        </View>
      );
    }

    return this.props.children;
  }
}

// ============================================================
// LOADING SKELETON
// ============================================================

interface LoadingSkeletonProps {
  isShadow: boolean;
}

export function MapLoadingSkeleton({ isShadow }: LoadingSkeletonProps) {
  const pulseAnim = useRef(new Animated.Value(0.3)).current;

  useEffect(() => {
    const pulse = Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, {
          toValue: 0.7,
          duration: 800,
          useNativeDriver: true,
        }),
        Animated.timing(pulseAnim, {
          toValue: 0.3,
          duration: 800,
          useNativeDriver: true,
        }),
      ]),
    );
    pulse.start();
    return () => pulse.stop();
  }, []);

  return (
    <View
      style={[
        styles.skeletonContainer,
        {
          backgroundColor: isShadow ? "#1A1025" : "#F3F4F6",
        },
      ]}
    >
      <Animated.View style={[styles.skeletonPulse, { opacity: pulseAnim }]}>
        <Text style={styles.skeletonEmoji}>🗺️</Text>
        <Text
          style={[
            styles.skeletonText,
            {
              color: isShadow ? "#6B7280" : "#9CA3AF",
            },
          ]}
        >
          Loading map...
        </Text>
      </Animated.View>
    </View>
  );
}

// ============================================================
// STYLES
// ============================================================

const styles = StyleSheet.create({
  // Offline
  offlineBanner: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    paddingVertical: 6,
    paddingHorizontal: 16,
    alignItems: "center",
    zIndex: 200,
  },
  offlineText: { color: "#FFF", fontSize: 12, fontWeight: "600" },

  // GPS
  gpsIndicator: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 10,
    gap: 4,
  },
  gpsDot: { width: 6, height: 6, borderRadius: 3 },
  gpsText: { fontSize: 10, fontWeight: "700" },
  gpsAccuracy: { fontSize: 9 },

  // Error
  errorContainer: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    padding: 40,
  },
  errorEmoji: { fontSize: 48, marginBottom: 16 },
  errorTitle: { fontSize: 20, fontWeight: "700", marginBottom: 8 },
  errorMessage: {
    fontSize: 14,
    textAlign: "center",
    lineHeight: 20,
    marginBottom: 24,
  },
  retryBtn: { paddingHorizontal: 24, paddingVertical: 12, borderRadius: 20 },
  retryText: { color: "#FFF", fontSize: 15, fontWeight: "700" },

  // Skeleton
  skeletonContainer: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  skeletonPulse: { alignItems: "center" },
  skeletonEmoji: { fontSize: 40, marginBottom: 12 },
  skeletonText: { fontSize: 14 },
});
