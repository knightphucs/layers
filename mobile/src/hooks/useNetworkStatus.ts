/**
 * LAYERS - Network Status Hook
 * Detects online/offline state in real-time
 *
 * WHY: Location-based apps are used OUTDOORS where signal drops.
 * We need to handle offline gracefully, not crash.
 *
 * USAGE:
 *   const { isConnected, isInternetReachable } = useNetworkStatus();
 *   if (!isConnected) showOfflineBanner();
 */

import { useState, useEffect, useCallback } from "react";
import NetInfo, { NetInfoState } from "@react-native-community/netinfo";

export interface NetworkStatus {
  isConnected: boolean;
  isInternetReachable: boolean | null;
  connectionType: string;
  isWifi: boolean;
}

export function useNetworkStatus() {
  const [status, setStatus] = useState<NetworkStatus>({
    isConnected: true,
    isInternetReachable: true,
    connectionType: "unknown",
    isWifi: false,
  });

  useEffect(() => {
    // Subscribe to network state changes
    const unsubscribe = NetInfo.addEventListener((state: NetInfoState) => {
      setStatus({
        isConnected: state.isConnected ?? false,
        isInternetReachable: state.isInternetReachable,
        connectionType: state.type,
        isWifi: state.type === "wifi",
      });
    });

    // Check initial state
    NetInfo.fetch().then((state: NetInfoState) => {
      setStatus({
        isConnected: state.isConnected ?? false,
        isInternetReachable: state.isInternetReachable,
        connectionType: state.type,
        isWifi: state.type === "wifi",
      });
    });

    return () => unsubscribe();
  }, []);

  // Manual refresh
  const refresh = useCallback(async () => {
    const state = await NetInfo.fetch();
    setStatus({
      isConnected: state.isConnected ?? false,
      isInternetReachable: state.isInternetReachable,
      connectionType: state.type,
      isWifi: state.type === "wifi",
    });
  }, []);

  return { ...status, refresh };
}
