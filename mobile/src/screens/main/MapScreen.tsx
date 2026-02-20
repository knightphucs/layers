// ===========================================
// LAYERS Map Screen (Day 5 Polish)
// Haptics, animations, network status, info card
// ===========================================

import React, { useRef, useEffect, useState, useCallback } from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Animated,
  Platform,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import MapView, { Marker, PROVIDER_GOOGLE, Circle } from "react-native-maps";
import { useAuthStore } from "../../store/authStore";
import { useLocation } from "../../hooks/useLocation";
import { useNetworkStatus } from "../../hooks/useNetworkStatus";
import { LocationStatus } from "../../components";
import { Colors } from "../../constants/colors";
import { Config } from "../../constants/config";
import { haptics } from "../../utils/haptics";

// Shadow Layer map style
const SHADOW_MAP_STYLE = [
  { elementType: "geometry", stylers: [{ color: "#1a1a2e" }] },
  { elementType: "labels.text.stroke", stylers: [{ color: "#1a1a2e" }] },
  { elementType: "labels.text.fill", stylers: [{ color: "#6366f1" }] },
  {
    featureType: "road",
    elementType: "geometry",
    stylers: [{ color: "#2a2a4a" }],
  },
  {
    featureType: "road",
    elementType: "geometry.stroke",
    stylers: [{ color: "#3a3a5a" }],
  },
  {
    featureType: "water",
    elementType: "geometry",
    stylers: [{ color: "#0f0f23" }],
  },
  {
    featureType: "poi.park",
    elementType: "geometry",
    stylers: [{ color: "#1a2a1a" }],
  },
  {
    featureType: "transit",
    elementType: "geometry",
    stylers: [{ color: "#1a1a3a" }],
  },
];

export default function MapScreen() {
  const mapRef = useRef<MapView>(null);
  const [mapReady, setMapReady] = useState(false);

  // Auth store
  const { layer, toggleLayer } = useAuthStore();
  const isShadowMode = layer === "SHADOW";
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];

  // Location hook
  const {
    location,
    isLoading,
    error,
    hasPermission,
    isPermissionDenied,
    retry,
    getCurrentLocation,
    isWatching,
    watchLocation,
    stopWatching,
  } = useLocation({
    autoRequest: true,
    autoWatch: true,
    showDeniedAlert: true,
  });

  // Network status
  const { isConnected } = useNetworkStatus();

  // Animations
  const layerAnim = useRef(new Animated.Value(isShadowMode ? 1 : 0)).current;
  const pulseAnim = useRef(new Animated.Value(1)).current;

  // Animate layer toggle
  useEffect(() => {
    Animated.timing(layerAnim, {
      toValue: isShadowMode ? 1 : 0,
      duration: 300,
      useNativeDriver: false,
    }).start();
  }, [isShadowMode]);

  // Pulse animation for user marker
  useEffect(() => {
    const pulse = Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, {
          toValue: 1.3,
          duration: 1500,
          useNativeDriver: true,
        }),
        Animated.timing(pulseAnim, {
          toValue: 1,
          duration: 1500,
          useNativeDriver: true,
        }),
      ]),
    );
    pulse.start();
    return () => pulse.stop();
  }, []);

  // Center map on user when location updates
  useEffect(() => {
    if (location && mapReady && mapRef.current) {
      mapRef.current.animateToRegion(
        {
          latitude: location.latitude,
          longitude: location.longitude,
          latitudeDelta: 0.005,
          longitudeDelta: 0.005,
        },
        500,
      );
    }
  }, [location?.latitude, location?.longitude, mapReady]);

  // Handle layer toggle with haptics
  const handleLayerToggle = useCallback(() => {
    haptics.impact();
    toggleLayer();
  }, [toggleLayer]);

  // Recenter map on user
  const handleRecenter = useCallback(() => {
    haptics.light();
    if (location && mapRef.current) {
      mapRef.current.animateToRegion(
        {
          latitude: location.latitude,
          longitude: location.longitude,
          latitudeDelta: 0.005,
          longitudeDelta: 0.005,
        },
        500,
      );
    } else {
      getCurrentLocation();
    }
  }, [location, getCurrentLocation]);

  // Create artifact button
  const handleCreateArtifact = useCallback(() => {
    if (!location) {
      return;
    }
    haptics.success();
    // TODO Week 3: Navigate to create artifact screen
  }, [location]);

  // Render loading or permission denied state
  if ((isLoading && !location) || isPermissionDenied) {
    return (
      <LocationStatus
        isLoading={isLoading}
        hasPermission={hasPermission}
        isPermissionDenied={isPermissionDenied}
        error={error}
        onRetry={retry}
        compact={false}
      />
    );
  }

  return (
    <View style={styles.container}>
      {/* Map */}
      <MapView
        ref={mapRef}
        style={styles.map}
        provider={Platform.OS === "android" ? PROVIDER_GOOGLE : undefined}
        initialRegion={{
          latitude: location?.latitude || Config.MAP_DEFAULT_REGION.latitude,
          longitude: location?.longitude || Config.MAP_DEFAULT_REGION.longitude,
          latitudeDelta: Config.MAP_DEFAULT_REGION.latitudeDelta,
          longitudeDelta: Config.MAP_DEFAULT_REGION.longitudeDelta,
        }}
        showsUserLocation={false}
        showsMyLocationButton={false}
        showsCompass={false}
        rotateEnabled={false}
        customMapStyle={isShadowMode ? SHADOW_MAP_STYLE : []}
        userInterfaceStyle={isShadowMode ? "dark" : "light"}
        onMapReady={() => setMapReady(true)}
      >
        {/* User Location Marker */}
        {location && (
          <>
            {/* Proof of Presence radius (50m) */}
            <Circle
              center={location}
              radius={Config.GEO.UNLOCK_RADIUS_METERS}
              fillColor={
                isShadowMode
                  ? "rgba(139, 92, 246, 0.08)"
                  : "rgba(59, 130, 246, 0.08)"
              }
              strokeColor={
                isShadowMode
                  ? "rgba(139, 92, 246, 0.4)"
                  : "rgba(59, 130, 246, 0.4)"
              }
              strokeWidth={1.5}
            />

            {/* User marker */}
            <Marker coordinate={location} anchor={{ x: 0.5, y: 0.5 }}>
              <View style={styles.markerContainer}>
                <Animated.View
                  style={[
                    styles.markerOuter,
                    {
                      backgroundColor: isShadowMode
                        ? "rgba(139, 92, 246, 0.2)"
                        : "rgba(59, 130, 246, 0.2)",
                      transform: [{ scale: pulseAnim }],
                    },
                  ]}
                />
                <View
                  style={[
                    styles.markerInner,
                    {
                      backgroundColor: isShadowMode ? "#8B5CF6" : "#3B82F6",
                    },
                  ]}
                />
              </View>
            </Marker>
          </>
        )}
      </MapView>

      {/* Header Overlay */}
      <SafeAreaView edges={["top"]} style={styles.headerOverlay}>
        {/* Layer Toggle */}
        <TouchableOpacity
          style={[styles.layerToggle, { backgroundColor: colors.surface }]}
          onPress={handleLayerToggle}
          activeOpacity={0.7}
        >
          <Text style={styles.layerIcon}>{isShadowMode ? "🌙" : "☀️"}</Text>
          <Text style={[styles.layerText, { color: colors.text }]}>
            {isShadowMode ? "Shadow" : "Light"}
          </Text>
        </TouchableOpacity>

        <View style={styles.headerRight}>
          {/* Connection Status */}
          {!isConnected && (
            <View style={styles.offlineChip}>
              <Text style={styles.offlineText}>📡 Offline</Text>
            </View>
          )}

          {/* Location Status */}
          <View
            style={[styles.statusBadge, { backgroundColor: colors.surface }]}
          >
            <Text style={styles.statusIcon}>{isWatching ? "📍" : "📌"}</Text>
            <Text style={[styles.statusText, { color: colors.textSecondary }]}>
              {isWatching ? "Live" : "Static"}
            </Text>
          </View>
        </View>
      </SafeAreaView>

      {/* Bottom Controls */}
      <View style={styles.bottomControls}>
        {/* Info Chip */}
        {location && (
          <View style={styles.infoChipRow}>
            <View
              style={[styles.infoChip, { backgroundColor: colors.surface }]}
            >
              <Text style={styles.infoChipIcon}>📍</Text>
              <Text style={[styles.infoChipText, { color: colors.text }]}>
                {location.latitude.toFixed(4)}, {location.longitude.toFixed(4)}
              </Text>
            </View>
            <View
              style={[styles.infoChip, { backgroundColor: colors.surface }]}
            >
              <Text style={styles.infoChipIcon}>
                {isShadowMode ? "👻" : "💌"}
              </Text>
              <Text style={[styles.infoChipText, { color: colors.primary }]}>
                {isShadowMode ? "0 glitch zones" : "0 nearby"}
              </Text>
            </View>
          </View>
        )}

        {/* Action Buttons */}
        <View style={styles.actionButtons}>
          {/* Recenter */}
          <TouchableOpacity
            style={[styles.actionBtn, { backgroundColor: colors.surface }]}
            onPress={handleRecenter}
            activeOpacity={0.7}
          >
            <Text style={styles.actionIcon}>🎯</Text>
          </TouchableOpacity>

          {/* Create Artifact */}
          <TouchableOpacity
            style={[styles.createBtn, { backgroundColor: colors.primary }]}
            onPress={handleCreateArtifact}
            activeOpacity={0.7}
          >
            <Text style={styles.createIcon}>✏️</Text>
            <Text style={styles.createLabel}>Create</Text>
          </TouchableOpacity>

          {/* Toggle Watch */}
          <TouchableOpacity
            style={[styles.actionBtn, { backgroundColor: colors.surface }]}
            onPress={() => {
              haptics.selection();
              isWatching ? stopWatching() : watchLocation();
            }}
            activeOpacity={0.7}
          >
            <Text style={styles.actionIcon}>{isWatching ? "⏸️" : "▶️"}</Text>
          </TouchableOpacity>
        </View>
      </View>

      {/* Error Toast */}
      {error && (
        <LocationStatus
          isLoading={false}
          hasPermission={hasPermission}
          isPermissionDenied={false}
          error={error}
          onRetry={retry}
          compact={true}
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  map: {
    flex: 1,
  },

  // User Marker
  markerContainer: {
    width: 32,
    height: 32,
    alignItems: "center",
    justifyContent: "center",
  },
  markerOuter: {
    position: "absolute",
    width: 32,
    height: 32,
    borderRadius: 16,
  },
  markerInner: {
    width: 14,
    height: 14,
    borderRadius: 7,
    borderWidth: 2.5,
    borderColor: "#FFFFFF",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 4,
    elevation: 4,
  },

  // Header
  headerOverlay: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    paddingHorizontal: 16,
    paddingTop: 8,
  },
  headerRight: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
  },
  layerToggle: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 20,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.15,
    shadowRadius: 8,
    elevation: 4,
  },
  layerIcon: {
    fontSize: 18,
    marginRight: 8,
  },
  layerText: {
    fontSize: 14,
    fontWeight: "600",
  },
  statusBadge: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 16,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 2,
  },
  statusIcon: {
    fontSize: 14,
    marginRight: 4,
  },
  statusText: {
    fontSize: 12,
    fontWeight: "500",
  },
  offlineChip: {
    backgroundColor: "#EF4444",
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 12,
  },
  offlineText: {
    color: "#FFF",
    fontSize: 12,
    fontWeight: "600",
  },

  // Info Chips
  infoChipRow: {
    flexDirection: "row",
    justifyContent: "center",
    gap: 10,
    marginBottom: 14,
  },
  infoChip: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 14,
    paddingVertical: 9,
    borderRadius: 20,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  infoChipIcon: {
    fontSize: 13,
    marginRight: 6,
  },
  infoChipText: {
    fontSize: 12,
    fontWeight: "600",
    letterSpacing: 0.3,
  },

  // Bottom Controls
  bottomControls: {
    position: "absolute",
    bottom: Platform.OS === "ios" ? 100 : 80,
    left: 16,
    right: 16,
  },
  actionButtons: {
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    gap: 12,
  },
  actionBtn: {
    width: 48,
    height: 48,
    borderRadius: 24,
    justifyContent: "center",
    alignItems: "center",
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.15,
    shadowRadius: 8,
    elevation: 4,
  },
  actionIcon: {
    fontSize: 22,
  },
  createBtn: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 20,
    paddingVertical: 14,
    borderRadius: 28,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.25,
    shadowRadius: 8,
    elevation: 6,
  },
  createIcon: {
    fontSize: 18,
    marginRight: 8,
  },
  createLabel: {
    color: "#FFF",
    fontSize: 15,
    fontWeight: "700",
  },
});
