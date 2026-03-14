/**
 * LAYERS - MapScreen
 * ====================================
 * Tích hợp toàn diện & Performance Polish:
 * ✅ Polish: Error Boundaries, Offline Banner, Loading Skeleton, GPS Accuracy.
 * ✅ Performance: Debounced fetch (300ms), Throttled fog (2s), Layer change force refetch.
 * ✅ Fog of War: Sương mù, Animations, Stats Bar.
 * ✅ Controls & UI: Haptics, Info Chips, 4 Action Buttons (Recenter, Drop, Toggle Fog, Watch GPS).
 * ✅ Artifact: Create Sheet, Detail Sheet, Passcode Unlock, Drop Animations.
 * ✅ Clustering: Render mượt mà marker và cluster.
 */

import React, { useState, useRef, useCallback, useEffect } from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Animated,
  Platform,
  Alert,
  Dimensions,
} from "react-native";
import MapView, {
  Marker,
  Circle,
  PROVIDER_GOOGLE,
  Region,
} from "react-native-maps";
import { SafeAreaView } from "react-native-safe-area-context";

// Stores & Hooks
import { useAuthStore } from "../../store/authStore";
import { useArtifactStore } from "../../store/artifactStore";
import { useLocation } from "../../hooks/useLocation";
import { useNetworkStatus } from "../../hooks/useNetworkStatus";
import { useExploration } from "../../hooks/useExploration";
import { useFogOfWar } from "../../hooks/useFogOfWar";
import { useCreateArtifact } from "../../hooks/useCreateArtifact";
import { useArtifactDetail } from "../../hooks/useArtifactDetail";
import { useMapPerformance } from "../../hooks/useMapPerformance";
import { useMarkerClusters } from "../../components/map/MarkerCluster";

// Components
import { LocationStatus } from "../../components";
import FogOverlay from "../../components/map/FogOverlay";
import FogStatsBar from "../../components/map/FogStatsBar";
import FogClearAnimation from "../../components/map/FogClearAnimation";
import ArtifactMarkerComponent from "../../components/map/ArtifactMarker";
import { ClusterMarker } from "../../components/map/MarkerCluster";
import CreateArtifactSheet from "../../components/create/CreateArtifactSheet";
import DropAnimation from "../../components/create/DropAnimation";
import ArtifactDetailSheet from "../../components/detail/ArtifactDetailSheet";
import {
  OfflineBanner,
  GPSAccuracyIndicator,
  MapErrorBoundary,
  MapLoadingSkeleton,
} from "../../components/map/StatusOverLays";

// Constants & Utils
import { Colors } from "../../constants/colors";
import { Config } from "../../constants/config";
import { haptics } from "../../utils/haptics";
import { ArtifactMarker as ArtifactMarkerType } from "../../types/artifact";

const { width: SCREEN_WIDTH } = Dimensions.get("window");

// Shadow Layer map style
const SHADOW_MAP_STYLE = [
  { elementType: "geometry", stylers: [{ color: "#1a1025" }] },
  { elementType: "labels.text.fill", stylers: [{ color: "#8B5CF6" }] },
  { elementType: "labels.text.stroke", stylers: [{ color: "#0a0510" }] },
  {
    featureType: "road",
    elementType: "geometry",
    stylers: [{ color: "#2d1f42" }],
  },
  {
    featureType: "water",
    elementType: "geometry",
    stylers: [{ color: "#0d0620" }],
  },
  {
    featureType: "poi",
    elementType: "geometry",
    stylers: [{ color: "#1f1535" }],
  },
  {
    featureType: "transit",
    elementType: "geometry",
    stylers: [{ color: "#1a1030" }],
  },
];

// ============================================================
// INNER MAP COMPONENT (wrapped by ErrorBoundary)
// ============================================================

function MapScreenInner() {
  // ---- MAP REF & STATE ----
  const mapRef = useRef<MapView>(null);
  const [mapReady, setMapReady] = useState(false);
  const [currentRegion, setCurrentRegion] = useState<Region | null>(null);
  const [showFog, setShowFog] = useState(true);

  // ---- AUTH & THEME ----
  const { layer, toggleLayer } = useAuthStore();
  const isShadowMode = layer.toUpperCase() === "SHADOW";
  const colors = Colors[isShadowMode ? "shadow" : "light"];

  // ---- LOCATION & NETWORK ----
  const {
    location,
    accuracy,
    isLoading,
    error: locationError,
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

  const { isConnected } = useNetworkStatus();

  // ---- ARTIFACT STORE ----
  const {
    nearbyArtifacts,
    fetchNearby,
    selectArtifact,
    selectedArtifact,
    clearSelection,
  } = useArtifactStore();

  // ---- FOG OF WAR ----
  const {
    exploredChunks,
    fogPercentage,
    clearEvent,
    newChunkFlash,
    totalStats,
    fetchViewportChunks,
    onNewChunksExplored,
  } = useFogOfWar();

  // ---- EXPLORATION ----
  const { isExploring, bufferSize } = useExploration(location, {
    onNewChunks: onNewChunksExplored,
  });

  // ---- ARTIFACT CREATION ----
  const {
    isSheetOpen,
    openSheet,
    closeSheet,
    handleSubmit: handleCreateSubmit,
    dropAnim,
    handleAnimComplete,
    error: createError,
  } = useCreateArtifact();

  // ---- ARTIFACT DETAIL ----
  const {
    isDetailOpen,
    detailData,
    isLoading: isDetailLoading,
    openDetail,
    closeDetail,
    unlockPasscode,
    sendReply,
  } = useArtifactDetail();

  // ---- PERFORMANCE HOOK (Day 5) ----
  const { handleRegionChange: debouncedRegionChange, forceRefetch } =
    useMapPerformance({
      onFetchArtifacts: fetchNearby,
      onFetchFog: fetchViewportChunks,
      layer: isShadowMode ? "SHADOW" : "LIGHT",
      radius: Config.GEO?.NEARBY_RADIUS_DEFAULT || 1000,
    });

  // ---- CLUSTERING ----
  const {
    items: mapItems,
    clusters,
    showClusters,
    markers,
  } = useMarkerClusters(nearbyArtifacts, currentRegion);

  // ---- ANIMATIONS ----
  const pulseAnim = useRef(new Animated.Value(1)).current;

  // ========================================================
  // EFFECTS
  // ========================================================

  useEffect(() => {
    const pulse = Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, {
          toValue: 1.4,
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
  }, [pulseAnim]);

  // Center map on user when location updates initially
  useEffect(() => {
    if (location && mapReady && mapRef.current && !currentRegion) {
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

  // Show create errors
  useEffect(() => {
    if (createError) Alert.alert("Oops!", createError);
  }, [createError]);

  // Force refetch when layer changes
  useEffect(() => {
    if (location && mapReady) {
      forceRefetch(location.latitude, location.longitude);
    }
  }, [isShadowMode]);

  // ========================================================
  // HANDLERS
  // ========================================================

  const handleRegionChange = useCallback(
    (region: Region) => {
      setCurrentRegion(region);
      debouncedRegionChange(region);
    },
    [debouncedRegionChange],
  );

  const handleLayerToggle = useCallback(() => {
    haptics.impact();
    toggleLayer();
  }, [toggleLayer]);

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

  const handleCreateArtifact = useCallback(() => {
    if (!location) return;
    haptics.success();
    openSheet();
  }, [location, openSheet]);

  const handleMarkerPress = useCallback(
    (artifact: ArtifactMarkerType | string) => {
      haptics.light();
      const artifactId = typeof artifact === "string" ? artifact : artifact.id;
      const artifactObj =
        typeof artifact === "string"
          ? nearbyArtifacts.find((a) => a.id === artifactId)
          : artifact;

      if (artifactObj) {
        selectArtifact(artifactObj);
        openDetail(artifactId);
      }
    },
    [selectArtifact, openDetail, nearbyArtifacts],
  );

  const handleDetailClose = useCallback(() => {
    closeDetail();
    clearSelection();
  }, [closeDetail, clearSelection]);

  const handleCreateComplete = useCallback(() => {
    handleAnimComplete();
    // Force refetch để marker mới hiện lên ngay
    if (location) forceRefetch(location.latitude, location.longitude);
  }, [handleAnimComplete, location, forceRefetch]);

  // ========================================================
  // RENDER
  // ========================================================

  // Day 4: Render permission denied state
  if ((isLoading && !location) || isPermissionDenied) {
    return (
      <LocationStatus
        isLoading={isLoading}
        hasPermission={hasPermission}
        isPermissionDenied={isPermissionDenied}
        error={locationError}
        onRetry={retry}
        compact={false}
      />
    );
  }

  // Show skeleton while waiting for first map load & GPS
  if (!location && !mapReady) {
    return <MapLoadingSkeleton isShadow={isShadowMode} />;
  }

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      {/* ======== MAP ======== */}
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
        onRegionChangeComplete={handleRegionChange}
        moveOnMarkerPress={false} // Feature: Prevent map jumping
      >
        {/* Fog of War Overlay */}
        {mapReady && showFog && (
          <FogOverlay
            exploredChunks={exploredChunks}
            mapRegion={currentRegion}
          />
        )}

        {/* User Location Marker */}
        {location && (
          <>
            <Circle
              center={location}
              radius={Config.GEO.UNLOCK_RADIUS_METERS || 50}
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
              zIndex={20}
            />
            <Marker
              coordinate={location}
              anchor={{ x: 0.5, y: 0.5 }}
              zIndex={30}
            >
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
                    { backgroundColor: isShadowMode ? "#8B5CF6" : "#3B82F6" },
                  ]}
                />
              </View>
            </Marker>
          </>
        )}

        {/* Artifact & Cluster Markers */}
        {mapReady &&
          mapItems?.map((item) => {
            if (item.type === "cluster") {
              return (
                <ClusterMarker
                  key={item.id}
                  cluster={item}
                  isShadow={isShadowMode}
                  onPress={() => {
                    if (mapRef.current && currentRegion) {
                      mapRef.current.animateToRegion(
                        {
                          latitude: item.coordinate.latitude,
                          longitude: item.coordinate.longitude,
                          latitudeDelta: currentRegion.latitudeDelta / 3,
                          longitudeDelta: currentRegion.longitudeDelta / 3,
                        },
                        400,
                      );
                    }
                  }}
                />
              );
            }
            return (
              <ArtifactMarkerComponent
                key={item.id}
                artifact={item.artifact}
                isShadow={isShadowMode}
                isSelected={selectedArtifact?.id === item.artifact.id}
                onPress={() => handleMarkerPress(item.artifact)}
              />
            );
          })}
      </MapView>

      {/* ======== ANIMATIONS & OVERLAYS ======== */}
      {clearEvent && (
        <View style={styles.clearAnimContainer} pointerEvents="none">
          <FogClearAnimation clearEvent={clearEvent} />
        </View>
      )}

      <DropAnimation
        emoji={dropAnim.emoji}
        visible={dropAnim.visible}
        onComplete={handleCreateComplete}
        isShadow={isShadowMode}
      />

      <OfflineBanner isShadow={isShadowMode} />

      {/* ======== HEADER (GPS/Offline) ======== */}
      <SafeAreaView edges={["top"]} style={styles.headerOverlay}>
        <View style={styles.headerTopRow}>
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
            {!isConnected && (
              <View style={styles.offlineChip}>
                <Text style={styles.offlineText}>📡 Offline</Text>
              </View>
            )}

            {/* GPS Indicator */}
            <GPSAccuracyIndicator
              accuracy={accuracy ?? 0}
              isShadow={isShadowMode}
            />

            {nearbyArtifacts.length > 0 && (
              <View
                style={[
                  styles.statusBadge,
                  { backgroundColor: colors.surface },
                ]}
              >
                <Text style={styles.statusIcon}>
                  {isShadowMode ? "👻" : "💌"}
                </Text>
                <Text style={[styles.statusText, { color: colors.primary }]}>
                  {nearbyArtifacts.length} nearby
                </Text>
              </View>
            )}

            {isExploring && bufferSize > 0 && (
              <View
                style={[
                  styles.statusBadge,
                  { backgroundColor: colors.surface },
                ]}
              >
                <Text style={styles.statusIcon}>🗺️</Text>
                <Text
                  style={[styles.statusText, { color: colors.textSecondary }]}
                >
                  {bufferSize}pts
                </Text>
              </View>
            )}

            <View
              style={[styles.statusBadge, { backgroundColor: colors.surface }]}
            >
              <Text style={styles.statusIcon}>{isWatching ? "📍" : "📌"}</Text>
              <Text
                style={[styles.statusText, { color: colors.textSecondary }]}
              >
                {isWatching ? "Live" : "Static"}
              </Text>
            </View>
          </View>
        </View>

        <View style={styles.fogStatsContainer}>
          <FogStatsBar
            fogPercentage={fogPercentage}
            totalExplored={totalStats.totalChunksAllTime}
            newChunkFlash={newChunkFlash}
          />
        </View>
      </SafeAreaView>

      {/* ======== BOTTOM CONTROLS ======== */}
      <SafeAreaView edges={["bottom"]} style={styles.bottomControls}>
        {/* Info Chips */}
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
                {nearbyArtifacts.filter((a) => a.is_within_range).length}{" "}
                {isShadowMode ? "glitch zones" : "unlockable"}
              </Text>
            </View>
          </View>
        )}

        {/* Action Buttons */}
        <View style={styles.actionButtons}>
          <TouchableOpacity
            style={[styles.actionBtn, { backgroundColor: colors.surface }]}
            onPress={handleRecenter}
            activeOpacity={0.7}
          >
            <Text style={styles.actionIcon}>🎯</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[
              styles.createBtn,
              { backgroundColor: isShadowMode ? "#8B5CF6" : "#3B82F6" },
            ]}
            onPress={handleCreateArtifact}
            activeOpacity={0.7}
          >
            <Text style={styles.createIcon}>{isShadowMode ? "🌙" : "✉️"}</Text>
            <Text style={styles.createLabel}>
              {isShadowMode ? "Drop Shadow" : "Drop Memory"}
            </Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.actionBtn, { backgroundColor: colors.surface }]}
            onPress={() => setShowFog(!showFog)}
            activeOpacity={0.7}
          >
            <Text style={styles.actionIcon}>{showFog ? "🌫️" : "👁️"}</Text>
          </TouchableOpacity>

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
      </SafeAreaView>

      {/* ======== SHEETS ======== */}
      <CreateArtifactSheet
        visible={isSheetOpen}
        onClose={closeSheet}
        onSubmit={handleCreateSubmit}
        isShadow={isShadowMode}
        currentLayer={isShadowMode ? "SHADOW" : "LIGHT"}
      />

      <ArtifactDetailSheet
        visible={isDetailOpen}
        data={detailData}
        isLoading={isDetailLoading}
        onClose={handleDetailClose}
        onUnlockPasscode={unlockPasscode}
        onReply={sendReply}
        isShadow={isShadowMode}
      />

      {/* Error Toast */}
      {locationError && (
        <LocationStatus
          isLoading={false}
          hasPermission={hasPermission}
          isPermissionDenied={false}
          error={locationError}
          onRetry={retry}
          compact={true}
        />
      )}
    </View>
  );
}

// ============================================================
// EXPORTED COMPONENT (wrapped with ErrorBoundary)
// ============================================================

export default function MapScreen() {
  const { layer } = useAuthStore();
  const isShadowMode = layer.toUpperCase() === "SHADOW";

  return (
    <MapErrorBoundary isShadow={isShadowMode}>
      <MapScreenInner />
    </MapErrorBoundary>
  );
}

// ============================================================
// STYLES
// ============================================================

const styles = StyleSheet.create({
  container: { flex: 1 },
  map: { flex: 1 },

  // User Marker
  markerContainer: {
    width: 40,
    height: 40,
    alignItems: "center",
    justifyContent: "center",
  },
  markerOuter: {
    position: "absolute",
    width: 36,
    height: 36,
    borderRadius: 18,
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

  // Header Overlay
  headerOverlay: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    paddingHorizontal: 16,
    paddingTop: 8,
  },
  headerTopRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-start",
    marginBottom: 8,
  },
  headerRight: {
    flexDirection: "row",
    alignItems: "center",
    flexWrap: "wrap",
    justifyContent: "flex-end",
    gap: 8,
    flex: 1,
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
    marginRight: 8,
  },
  layerIcon: { fontSize: 18, marginRight: 8 },
  layerText: { fontSize: 14, fontWeight: "600" },

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
    marginBottom: 4,
  },
  statusIcon: { fontSize: 14, marginRight: 4 },
  statusText: { fontSize: 12, fontWeight: "500" },

  offlineChip: {
    backgroundColor: "#EF4444",
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 12,
    marginBottom: 4,
  },
  offlineText: { color: "#FFF", fontSize: 12, fontWeight: "600" },

  fogStatsContainer: { marginHorizontal: 0 },

  // Fog Anim
  clearAnimContainer: {
    position: "absolute",
    top: "50%",
    left: "50%",
    marginLeft: -50,
    marginTop: -50,
    zIndex: 100,
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
  infoChipIcon: { fontSize: 13, marginRight: 6 },
  infoChipText: { fontSize: 12, fontWeight: "600", letterSpacing: 0.3 },

  // Bottom Controls
  bottomControls: {
    position: "absolute",
    bottom: 0,
    left: 16,
    right: 16,
    paddingBottom: Platform.OS === "ios" ? 10 : 20,
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
  actionIcon: { fontSize: 22 },
  createBtn: {
    flex: 1,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 20,
    paddingVertical: 14,
    borderRadius: 28,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.25,
    shadowRadius: 8,
    elevation: 6,
  },
  createIcon: { fontSize: 18, marginRight: 8 },
  createLabel: { color: "#FFF", fontSize: 15, fontWeight: "700" },
});
