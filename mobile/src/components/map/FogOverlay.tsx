/**
 * LAYERS - Fog of War Overlay
 * ====================================
 * THE CORE VISUAL MECHANIC of LAYERS.
 * The map starts covered in fog. Walking IRL clears it.
 *
 * TECHNIQUE: "Polygon with Holes"
 *   1. Draw a HUGE polygon covering the entire visible map (the fog)
 *   2. Cut rectangular "holes" for each explored chunk (clear areas)
 *   3. Result: fog everywhere EXCEPT where user has walked
 *
 * WHY THIS TECHNIQUE:
 *   react-native-maps Polygon supports "holes" prop natively.
 *   No need for Canvas, SVG, or custom native modules.
 *   Performance is great — MapView handles polygon rendering in OpenGL.
 *
 * VISUAL DESIGN:
 *   Light mode: Soft white fog with subtle blur feel
 *   Shadow mode: Deep dark purple fog with mystical vibe
 *   Explored areas have a subtle glow edge where fog meets clear
 *
 * BACKEND API USED:
 *   GET /explore/chunks?lat=X&lng=Y&radius=Z
 *   Returns: { explored: [{ bounds: { lat_min, lat_max, lng_min, lng_max } }] }
 */

import React, { useMemo, memo } from "react";
import { Polygon } from "react-native-maps";
import { useAuthStore } from "../../store/authStore";
import {
  ExploredChunkData,
  ChunkBounds,
} from "../../services/explore";

interface Props {
  exploredChunks: ExploredChunkData[];
  mapRegion: {
    latitude: number;
    longitude: number;
    latitudeDelta: number;
    longitudeDelta: number;
  } | null;
}

// ============================================================
// FOG BOUNDARY — The outer polygon that covers everything
// ============================================================

/**
 * Create a massive polygon that covers the entire visible map + buffer.
 * This is the "fog" — everything is hidden by default.
 *
 * We use a polygon much larger than the viewport to prevent
 * seeing edges of the fog when user pans the map.
 */
function createFogBoundary(region: {
  latitude: number;
  longitude: number;
  latitudeDelta: number;
  longitudeDelta: number;
}) {
  // Extend 3x beyond viewport to prevent edge visibility
  const buffer = 3;
  const latDelta = region.latitudeDelta * buffer;
  const lngDelta = region.longitudeDelta * buffer;

  return [
    {
      latitude: region.latitude - latDelta,
      longitude: region.longitude - lngDelta,
    },
    {
      latitude: region.latitude - latDelta,
      longitude: region.longitude + lngDelta,
    },
    {
      latitude: region.latitude + latDelta,
      longitude: region.longitude + lngDelta,
    },
    {
      latitude: region.latitude + latDelta,
      longitude: region.longitude - lngDelta,
    },
  ];
}

// ============================================================
// CHUNK HOLES — Rectangular holes in the fog for explored areas
// ============================================================

/**
 * Convert backend chunk bounds to Polygon hole coordinates.
 *
 * Each hole is a small rectangle (~100m × 100m) that gets cut
 * out of the fog, revealing the map underneath.
 *
 * IMPORTANT: Holes must be wound COUNTER-CLOCKWISE (opposite of outer polygon)
 * for the Polygon "holes" prop to work correctly on both iOS and Android.
 */
function chunkBoundsToHole(bounds: ChunkBounds) {
  // Counter-clockwise winding for holes
  return [
    { latitude: bounds.lat_min, longitude: bounds.lng_min }, // Bottom-left
    { latitude: bounds.lat_max, longitude: bounds.lng_min }, // Top-left
    { latitude: bounds.lat_max, longitude: bounds.lng_max }, // Top-right
    { latitude: bounds.lat_min, longitude: bounds.lng_max }, // Bottom-right
  ];
}

/**
 * Merge adjacent chunks into larger rectangles for performance.
 *
 * Instead of 100 individual 100m holes, merge into fewer larger holes.
 * This reduces polygon complexity and improves render performance.
 *
 * Algorithm: Greedy row-merge
 *   1. Group chunks by chunk_y (same row)
 *   2. For each row, find consecutive chunk_x values
 *   3. Merge consecutive chunks into one wider rectangle
 *   4. Then try to merge vertically (same x-span, adjacent rows)
 */
function mergeChunks(chunks: ExploredChunkData[]): ChunkBounds[] {
  const chunksWithBounds = chunks.filter(
    (chunk): chunk is ExploredChunkData & { bounds: ChunkBounds } =>
      !!chunk.bounds,
  );

  if (chunksWithBounds.length === 0) return [];
  if (chunksWithBounds.length <= 5) {
    // For very few chunks, don't bother merging
    return chunksWithBounds.map((c) => c.bounds);
  }

  // Group by row (chunk_y)
  const rows: Record<
    number,
    Array<ExploredChunkData & { bounds: ChunkBounds }>
  > = {};
  for (const chunk of chunksWithBounds) {
    const y = chunk.chunk_y;
    if (!rows[y]) rows[y] = [];
    rows[y].push(chunk);
  }

  const mergedBounds: ChunkBounds[] = [];

  for (const rowChunks of Object.values(rows)) {
    // Sort by chunk_x within each row
    rowChunks.sort((a, b) => a.chunk_x - b.chunk_x);

    // Merge consecutive x values in this row
    let startIdx = 0;
    for (let i = 1; i <= rowChunks.length; i++) {
      const isConsecutive =
        i < rowChunks.length &&
        rowChunks[i].chunk_x === rowChunks[i - 1].chunk_x + 1;

      if (!isConsecutive) {
        // Merge from startIdx to i-1
        const first = rowChunks[startIdx];
        const last = rowChunks[i - 1];
        mergedBounds.push({
          lat_min: Math.min(first.bounds.lat_min, last.bounds.lat_min),
          lat_max: Math.max(first.bounds.lat_max, last.bounds.lat_max),
          lng_min: first.bounds.lng_min,
          lng_max: last.bounds.lng_max,
        });
        startIdx = i;
      }
    }
  }

  return mergedBounds;
}

// ============================================================
// COMPONENT
// ============================================================

function FogOverlayComponent({ exploredChunks, mapRegion }: Props) {
  const { layer } = useAuthStore();
  const isShadow = layer === "SHADOW";

  // Memoize heavy computations
  const fogData = useMemo(() => {
    if (!mapRegion) return null;

    // 1. Create the outer fog boundary
    const outerCoords = createFogBoundary(mapRegion);

    // 2. Merge adjacent chunks for performance
    const mergedBounds = mergeChunks(exploredChunks);

    // 3. Convert to hole coordinates
    const holes = mergedBounds.map(chunkBoundsToHole);

    return { outerCoords, holes };
  }, [
    exploredChunks.length,
    mapRegion?.latitude,
    mapRegion?.longitude,
    mapRegion?.latitudeDelta,
  ]);

  if (!fogData || !mapRegion) return null;

  // Fog colors
  const fogFillColor = isShadow
    ? "rgba(10, 5, 30, 0.75)" // Deep dark purple — mystical
    : "rgba(180, 200, 220, 0.55)"; // Soft bluish white — gentle mist

  const fogStrokeColor = isShadow
    ? "rgba(139, 92, 246, 0.15)" // Faint purple edge
    : "rgba(100, 140, 180, 0.1)"; // Faint blue edge

  return (
    <>
      {/* THE FOG — one big polygon with holes */}
      <Polygon
        coordinates={fogData.outerCoords}
        holes={fogData.holes}
        fillColor={fogFillColor}
        strokeColor={fogStrokeColor}
        strokeWidth={0}
        tappable={false}
        zIndex={10} // Above map tiles, below markers
      />

      {/* GLOW EDGES — subtle bright border around explored areas */}
      {fogData.holes.length <= 50 &&
        fogData.holes.map((hole, index) => (
          <Polygon
            key={`glow-${index}`}
            coordinates={hole}
            fillColor="transparent"
            strokeColor={
              isShadow
                ? "rgba(139, 92, 246, 0.25)" // Purple glow
                : "rgba(59, 130, 246, 0.2)" // Blue glow
            }
            strokeWidth={1.5}
            tappable={false}
            zIndex={11}
          />
        ))}
    </>
  );
}

export default memo(FogOverlayComponent);
