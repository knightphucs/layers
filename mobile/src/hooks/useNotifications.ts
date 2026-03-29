/**
 * LAYERS — useNotifications Hook
 * ==========================================
 * Core hook that wires up the entire push notification system.
 *
 * RESPONSIBILITIES:
 *   1. Request notification permission on first use
 *   2. Get Expo push token → register with backend
 *   3. Handle incoming notifications (foreground + background)
 *   4. Deep link: tap notification → navigate to correct screen
 *   5. Manage notification channels (Android)
 *
 * USAGE:
 *   In App.tsx or RootNavigator:
 *     const { expoPushToken } = useNotifications();
 *
 */

import { useState, useEffect, useRef, useCallback } from "react";
import { Platform, AppState } from "react-native";
import * as Notifications from "expo-notifications";
import * as Device from "expo-device";
import Constants from "expo-constants";
import { notificationService } from "../services/notifications";
import { useNotificationStore } from "../store/notificationStore";
import { NotificationData } from "../types/notifications";

// ============================================================
// CONFIGURE NOTIFICATION HANDLER
// This runs BEFORE any component mounts.
// Controls how notifications appear when app is in foreground.
// ============================================================

Notifications.setNotificationHandler({
  handleNotification: async (notification) => {
    const data = notification.request.content
      .data as unknown as NotificationData;

    // Check quiet hours
    const store = useNotificationStore.getState();
    if (store.isInQuietHours()) {
      return {
        shouldShowAlert: false,
        shouldPlaySound: false,
        shouldSetBadge: false,
        shouldShowBanner: false,
        shouldShowList: false,
      };
    }

    // Check if category is enabled
    if (data?.category && !store.isCategoryEnabled(data.category)) {
      return {
        shouldShowAlert: false,
        shouldPlaySound: false,
        shouldSetBadge: false,
        shouldShowBanner: false,
        shouldShowList: false,
      };
    }

    return {
      shouldShowAlert: true,
      shouldPlaySound: true,
      shouldSetBadge: true,
      shouldShowBanner: true,
      shouldShowList: true,
    };
  },
});

// ============================================================
// HOOK
// ============================================================

interface UseNotificationsReturn {
  expoPushToken: string | null;
  hasPermission: boolean;
  isLoading: boolean;
  requestPermission: () => Promise<boolean>;
}

export function useNotifications(): UseNotificationsReturn {
  const [expoPushToken, setExpoPushToken] = useState<string | null>(null);
  const [hasPermission, setHasPermission] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  const notificationListener = useRef<Notifications.Subscription | null>(null);
  const responseListener = useRef<Notifications.Subscription | null>(null);

  const { addNotification, incrementBadge } = useNotificationStore();

  // ========================================================
  // REGISTER FOR PUSH NOTIFICATIONS
  // ========================================================

  const registerForPushNotifications = useCallback(async (): Promise<
    string | null
  > => {
    // Must be a physical device (not simulator for iOS)
    if (!Device.isDevice) {
      console.log("Push notifications require a physical device");
      return null;
    }

    // Check existing permission
    const { status: existingStatus } =
      await Notifications.getPermissionsAsync();
    let finalStatus = existingStatus;

    // Request if not granted
    if (existingStatus !== "granted") {
      const { status } = await Notifications.requestPermissionsAsync();
      finalStatus = status;
    }

    if (finalStatus !== "granted") {
      console.log("Push notification permission denied");
      setHasPermission(false);
      return null;
    }

    setHasPermission(true);

    // Get Expo push token
    try {
      const projectId =
        Constants.expoConfig?.extra?.eas?.projectId ??
        Constants.easConfig?.projectId;

      if (!projectId) {
        console.error(
          "❌ Missing EAS projectId — run `eas init` in /mobile and add the UUID to app.json under extra.eas.projectId",
        );
        return null;
      }

      const tokenData = await Notifications.getExpoPushTokenAsync({
        projectId,
      });

      const token = tokenData.data;
      console.log("📱 Expo Push Token:", token);

      // Register token with backend
      try {
        await notificationService.registerDeviceToken({
          token,
          platform: Platform.OS as "ios" | "android",
          device_name: Device.modelName || undefined,
        });
        console.log("✅ Device token registered with backend");
      } catch (err) {
        // Non-critical — token still works for local notifications
        console.warn("Failed to register token with backend:", err);
      }

      return token;
    } catch (error) {
      console.error("Failed to get push token:", error);
      return null;
    }
  }, []);

  // ========================================================
  // REQUEST PERMISSION (public method)
  // ========================================================

  const requestPermission = useCallback(async (): Promise<boolean> => {
    const token = await registerForPushNotifications();
    if (token) {
      setExpoPushToken(token);
      return true;
    }
    return false;
  }, [registerForPushNotifications]);

  // ========================================================
  // HANDLE NOTIFICATION RECEIVED (foreground)
  // ========================================================

  const handleNotificationReceived = useCallback(
    (notification: Notifications.Notification) => {
      const data = notification.request.content
        .data as unknown as NotificationData;

      if (__DEV__) {
        console.log("🔔 Notification received:", data?.type);
      }

      // Store in local notification list
      addNotification({
        id: notification.request.identifier,
        type: data?.type || "system",
        title: notification.request.content.title || "",
        body: notification.request.content.body || "",
        data,
        received_at: new Date().toISOString(),
        is_read: false,
      });

      incrementBadge();
    },
    [addNotification, incrementBadge],
  );

  // ========================================================
  // HANDLE NOTIFICATION TAPPED (deep link)
  // ========================================================

  const handleNotificationResponse = useCallback(
    (response: Notifications.NotificationResponse) => {
      const data = response.notification.request.content
        .data as unknown as NotificationData;

      if (__DEV__) {
        console.log("👆 Notification tapped:", data?.type, data?.screen);
      }

      // Deep link based on notification type
      if (data?.screen) {
        // TODO Week 5 Day 4: Wire up React Navigation deep linking
        // navigationRef.navigate(data.screen, data.params);
        console.log(`Navigate to: ${data.screen}`, data.params);
      }
    },
    [],
  );

  // ========================================================
  // SETUP ANDROID NOTIFICATION CHANNEL
  // ========================================================

  const setupAndroidChannels = useCallback(async () => {
    if (Platform.OS !== "android") return;

    await Notifications.setNotificationChannelAsync("social", {
      name: "Social",
      importance: Notifications.AndroidImportance.HIGH,
      vibrationPattern: [0, 250, 250, 250],
      lightColor: "#EC4899",
      description: "Replies, connections, and social interactions",
    });

    await Notifications.setNotificationChannelAsync("discovery", {
      name: "Discovery",
      importance: Notifications.AndroidImportance.DEFAULT,
      description: "Nearby artifacts and new discoveries",
    });

    await Notifications.setNotificationChannelAsync("inbox", {
      name: "Inbox",
      importance: Notifications.AndroidImportance.HIGH,
      vibrationPattern: [0, 250, 250, 250],
      lightColor: "#8B5CF6",
      description: "Slow Mail delivery and Paper Planes",
    });

    await Notifications.setNotificationChannelAsync("system", {
      name: "System",
      importance: Notifications.AndroidImportance.LOW,
      description: "Level ups, badges, and app updates",
    });
  }, []);

  // ========================================================
  // LIFECYCLE
  // ========================================================

  useEffect(() => {
    let mounted = true;

    const init = async () => {
      // Setup Android channels
      await setupAndroidChannels();

      // Register for push notifications
      const token = await registerForPushNotifications();
      if (mounted && token) {
        setExpoPushToken(token);
      }

      if (mounted) {
        setIsLoading(false);
      }
    };

    init();

    // Listen for notifications received while app is foregrounded
    notificationListener.current =
      Notifications.addNotificationReceivedListener(handleNotificationReceived);

    // Listen for notification taps (deep linking)
    responseListener.current =
      Notifications.addNotificationResponseReceivedListener(
        handleNotificationResponse,
      );

    // Cleanup
    return () => {
      mounted = false;
      if (notificationListener.current) {
        notificationListener.current.remove();
      }
      if (responseListener.current) {
        responseListener.current.remove();
      }
    };
  }, []);

  // Re-register token when app comes back to foreground
  // (token may have been rotated by OS)
  useEffect(() => {
    const subscription = AppState.addEventListener("change", (state) => {
      if (state === "active" && hasPermission) {
        registerForPushNotifications().then((token) => {
          if (token) setExpoPushToken(token);
        });
      }
    });

    return () => subscription.remove();
  }, [hasPermission]);

  return {
    expoPushToken,
    hasPermission,
    isLoading,
    requestPermission,
  };
}
