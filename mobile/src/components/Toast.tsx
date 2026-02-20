/**
 * LAYERS - Toast Notification System
 * Non-intrusive, auto-dismissing notifications
 *
 * WHY: Alerts (Alert.alert) block the UI. Toasts are gentle.
 * Used for: "Letter sent!", "Location updated", "New artifact found!"
 *
 * USAGE:
 *   import { useToast, ToastProvider } from './Toast';
 *
 *   // Wrap App
 *   <ToastProvider><App /></ToastProvider>
 *
 *   // In any component
 *   const toast = useToast();
 *   toast.show({ message: 'Letter sent! 💌', type: 'success' });
 */

import React, {
  createContext,
  useContext,
  useState,
  useCallback,
  useRef,
} from "react";
import {
  View,
  Text,
  StyleSheet,
  Animated,
  TouchableOpacity,
} from "react-native";

// ============================================================
// TYPES
// ============================================================

type ToastType = "success" | "error" | "info" | "warning";

interface ToastMessage {
  id: string;
  message: string;
  type: ToastType;
  duration?: number; // ms, default 3000
}

interface ToastContextType {
  show: (toast: Omit<ToastMessage, "id">) => void;
  success: (message: string) => void;
  error: (message: string) => void;
  info: (message: string) => void;
  warning: (message: string) => void;
}

// ============================================================
// CONTEXT
// ============================================================

const ToastContext = createContext<ToastContextType | null>(null);

export function useToast(): ToastContextType {
  const context = useContext(ToastContext);
  if (!context) throw new Error("useToast must be used within ToastProvider");
  return context;
}

// ============================================================
// STYLING PER TYPE
// ============================================================

const TOAST_CONFIG: Record<
  ToastType,
  { bg: string; icon: string; border: string }
> = {
  success: { bg: "#0D1B0F", icon: "✅", border: "#10B981" },
  error: { bg: "#1B0D0D", icon: "❌", border: "#EF4444" },
  info: { bg: "#0D141B", icon: "💡", border: "#3B82F6" },
  warning: { bg: "#1B170D", icon: "⚠️", border: "#F59E0B" },
};

// ============================================================
// SINGLE TOAST COMPONENT
// ============================================================

function ToastItem({
  toast,
  onDismiss,
}: {
  toast: ToastMessage;
  onDismiss: (id: string) => void;
}) {
  const opacity = useRef(new Animated.Value(0)).current;
  const translateY = useRef(new Animated.Value(-20)).current;
  const config = TOAST_CONFIG[toast.type];

  React.useEffect(() => {
    // Slide in
    Animated.parallel([
      Animated.timing(opacity, {
        toValue: 1,
        duration: 250,
        useNativeDriver: true,
      }),
      Animated.spring(translateY, {
        toValue: 0,
        useNativeDriver: true,
        tension: 100,
        friction: 15,
      }),
    ]).start();

    // Auto dismiss
    const timer = setTimeout(() => {
      Animated.parallel([
        Animated.timing(opacity, {
          toValue: 0,
          duration: 200,
          useNativeDriver: true,
        }),
        Animated.timing(translateY, {
          toValue: -20,
          duration: 200,
          useNativeDriver: true,
        }),
      ]).start(() => onDismiss(toast.id));
    }, toast.duration || 3000);

    return () => clearTimeout(timer);
  }, []);

  return (
    <Animated.View
      style={[
        styles.toast,
        {
          opacity,
          transform: [{ translateY }],
          borderLeftColor: config.border,
          backgroundColor: config.bg,
        },
      ]}
    >
      <TouchableOpacity
        style={styles.toastContent}
        activeOpacity={0.8}
        onPress={() => onDismiss(toast.id)}
      >
        <Text style={styles.icon}>{config.icon}</Text>
        <Text style={styles.message} numberOfLines={2}>
          {toast.message}
        </Text>
      </TouchableOpacity>
    </Animated.View>
  );
}

// ============================================================
// PROVIDER
// ============================================================

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  let counter = useRef(0);

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const show = useCallback((toast: Omit<ToastMessage, "id">) => {
    const id = `toast_${++counter.current}`;
    setToasts((prev) => [...prev.slice(-2), { ...toast, id }]); // Max 3 visible
  }, []);

  const contextValue: ToastContextType = {
    show,
    success: (message: string) => show({ message, type: "success" }),
    error: (message: string) => show({ message, type: "error" }),
    info: (message: string) => show({ message, type: "info" }),
    warning: (message: string) => show({ message, type: "warning" }),
  };

  return (
    <ToastContext.Provider value={contextValue}>
      {children}
      <View style={styles.container} pointerEvents="box-none">
        {toasts.map((toast) => (
          <ToastItem key={toast.id} toast={toast} onDismiss={dismiss} />
        ))}
      </View>
    </ToastContext.Provider>
  );
}

// ============================================================
// STYLES
// ============================================================

const styles = StyleSheet.create({
  container: {
    position: "absolute",
    top: 60,
    left: 16,
    right: 16,
    zIndex: 9998,
    gap: 8,
  },
  toast: {
    borderRadius: 12,
    borderLeftWidth: 4,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 8,
  },
  toastContent: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 12,
    paddingHorizontal: 16,
  },
  icon: {
    fontSize: 16,
    marginRight: 12,
  },
  message: {
    color: "#FFFFFF",
    fontSize: 14,
    fontWeight: "500",
    flex: 1,
  },
});
