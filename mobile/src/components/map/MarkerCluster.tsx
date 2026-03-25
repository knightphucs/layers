/**
 * LAYERS - Marker Clustering Utility
 * ====================================
 * FILE: mobile/src/components/map/MarkerCluster.tsx
 *
 * Groups nearby artifact markers into clusters when zoomed out.
 * This is CRITICAL for performance — rendering 200+ individual markers
 * would lag the map badly on mobile devices.
 *
 * ALGORITHM: Simple grid-based clustering
 *   1. Divide viewport into grid cells based on zoom level
 *   2. Group markers that fall in the same cell
 *   3. Show cluster bubble with count if > 1 marker in cell
 *   4. Show individual markers when zoomed in enough
 *
 * WHY NOT SUPERCLUSTER:
 *   We keep it simple for now. Supercluster lib can be added later
 *   if we need > 1000 markers. For MVP, grid clustering handles
 *   up to ~500 markers smoothly.
 */

import React, { useMemo, memo } from "react";
import { View, Text, StyleSheet, Platform } from "react-native";
import { Marker, Region } from "react-native-maps";
import { ArtifactMarker } from "../../types/artifact";

// ============================================================
// TYPES
// ============================================================

export interface Cluster {
  id: string;
  latitude: number;
  longitude: number;
  count: number;
  artifacts: ArtifactMarker[];
}

export interface ClusterMapItem extends Cluster {
  type: "cluster";
  coordinate: { latitude: number; longitude: number };
}

export interface MarkerMapItem {
  type: "marker";
  id: string;
  artifact: ArtifactMarker;
}

export type MapItem = ClusterMapItem | MarkerMapItem;

interface Props {
  artifacts: ArtifactMarker[];
  region: Region;
  onClusterPress: (cluster: Cluster) => void;
}

// ============================================================
// CLUSTERING LOGIC
// ============================================================

/**
 * Grid-based clustering. Fast and predictable.
 *
 * @param artifacts - All artifacts in viewport
 * @param region - Current map region (for zoom level)
 * @returns Array of clusters (some with count=1 = individual markers)
 */
export function clusterMarkers(
  artifacts: ArtifactMarker[],
  region: Region,
): Cluster[] {
  if (artifacts.length === 0) return [];

  // Determine grid cell size based on zoom level
  // Wider latitudeDelta = more zoomed out = bigger cells
  const cellSize = Math.max(region.latitudeDelta / 8, 0.0005);

  const grid: Record<string, ArtifactMarker[]> = {};

  for (const artifact of artifacts) {
    // Calculate grid cell key
    const cellX = Math.floor(artifact.longitude / cellSize);
    const cellY = Math.floor(artifact.latitude / cellSize);
    const key = `${cellX},${cellY}`;

    if (!grid[key]) grid[key] = [];
    grid[key].push(artifact);
  }

  // Convert grid cells to clusters
  return Object.entries(grid).map(([key, items]) => {
    // Cluster center = average of all marker positions
    const avgLat = items.reduce((sum, a) => sum + a.latitude, 0) / items.length;
    const avgLng =
      items.reduce((sum, a) => sum + a.longitude, 0) / items.length;

    return {
      id: key,
      latitude: avgLat,
      longitude: avgLng,
      count: items.length,
      artifacts: items,
    };
  });
}

/**
 * Should we show individual markers or clusters?
 * When zoomed in enough, show individual markers.
 */
export function shouldCluster(region: Region): boolean {
  // If latitudeDelta < 0.005, we're zoomed in enough for individual markers
  return region.latitudeDelta > 0.005;
}

// ============================================================
// CLUSTER MARKER COMPONENT
// ============================================================

function ClusterMarkerComponent({
  cluster,
  onPress,
}: {
  cluster: Cluster;
  onPress: (cluster: Cluster) => void;
  isShadow?: boolean;
}) {
  // Determine cluster color based on dominant artifact type
  const typeCounts: Record<string, number> = {};
  for (const a of cluster.artifacts) {
    typeCounts[a.content_type] = (typeCounts[a.content_type] || 0) + 1;
  }
  const dominantType = Object.entries(typeCounts).sort(
    (a, b) => b[1] - a[1],
  )[0][0];

  // Size scales with count
  const size = Math.min(28 + cluster.count * 4, 56);

  return (
    <Marker
      coordinate={{
        latitude: cluster.latitude,
        longitude: cluster.longitude,
      }}
      anchor={{ x: 0.5, y: 0.5 }}
      tracksViewChanges={false}
      onPress={() => onPress(cluster)}
    >
      <View
        style={[
          styles.clusterBubble,
          {
            width: size,
            height: size,
            borderRadius: size / 2,
          },
        ]}
      >
        <Text style={styles.clusterCount}>{cluster.count}</Text>
      </View>
    </Marker>
  );
}

export const ClusterMarker = memo(ClusterMarkerComponent);

// ============================================================
// HOOK - Use clustering in MapScreen
// ============================================================

/**
 * Custom hook that handles clustering logic.
 * Returns either clusters or individual markers based on zoom.
 */
export function useMarkerClusters(
  artifacts: ArtifactMarker[],
  region: Region | null,
) {
  return useMemo(() => {
    if (!region || artifacts.length === 0) {
      const items: MapItem[] = artifacts.map((a) => ({
        type: "marker" as const,
        id: a.id,
        artifact: a,
      }));
      return { clusters: [], showClusters: false, markers: artifacts, items };
    }

    const showClusters = shouldCluster(region);

    if (showClusters) {
      const clusters = clusterMarkers(artifacts, region);
      const items: MapItem[] = clusters.map((c) => ({
        ...c,
        type: "cluster" as const,
        coordinate: { latitude: c.latitude, longitude: c.longitude },
      }));
      return { clusters, showClusters: true, markers: [], items };
    }

    const items: MapItem[] = artifacts.map((a) => ({
      type: "marker" as const,
      id: a.id,
      artifact: a,
    }));
    return { clusters: [], showClusters: false, markers: artifacts, items };
  }, [artifacts, region?.latitudeDelta, region?.longitudeDelta]);
}

// ============================================================
// STYLES
// ============================================================

const styles = StyleSheet.create({
  clusterBubble: {
    backgroundColor: "rgba(99, 102, 241, 0.85)",
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 2.5,
    borderColor: "rgba(255, 255, 255, 0.9)",
    ...Platform.select({
      ios: {
        shadowColor: "#4F46E5",
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.3,
        shadowRadius: 4,
      },
      android: {
        elevation: 5,
      },
    }),
  },
  clusterCount: {
    color: "#FFFFFF",
    fontWeight: "bold",
    fontSize: 14,
  },
});
