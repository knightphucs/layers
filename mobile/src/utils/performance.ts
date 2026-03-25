/**
 * LAYERS - Performance Utilities
 * ====================================
 * Helpers to keep the map at 60fps.
 *
 * PROBLEMS SOLVED:
 *   1. onRegionChangeComplete fires rapidly → debounce API calls
 *   2. Fog fetch piles up during fast pan → throttle
 *   3. Unnecessary re-renders → shallow compare
 *   4. Distance formatting duplicated → centralize
 */

/**
 * Debounce — delay until caller stops invoking.
 * Use for: region change → API fetch
 */
export function debounce<T extends (...args: any[]) => any>(
  fn: T,
  delay: number,
): T & { cancel: () => void } {
  let timer: ReturnType<typeof setTimeout> | null = null;
  const debounced = ((...args: any[]) => {
    if (timer) clearTimeout(timer);
    timer = setTimeout(() => {
      fn(...args);
      timer = null;
    }, delay);
  }) as T & { cancel: () => void };
  debounced.cancel = () => {
    if (timer) {
      clearTimeout(timer);
      timer = null;
    }
  };
  return debounced;
}

/**
 * Throttle — max once per interval.
 * Use for: fog chunk fetch, GPS buffer
 */
export function throttle<T extends (...args: any[]) => any>(
  fn: T,
  interval: number,
): T & { cancel: () => void } {
  let lastCall = 0;
  let timer: ReturnType<typeof setTimeout> | null = null;
  const throttled = ((...args: any[]) => {
    const now = Date.now();
    const remaining = interval - (now - lastCall);
    if (remaining <= 0) {
      lastCall = now;
      fn(...args);
    } else if (!timer) {
      timer = setTimeout(() => {
        lastCall = Date.now();
        timer = null;
        fn(...args);
      }, remaining);
    }
  }) as T & { cancel: () => void };
  throttled.cancel = () => {
    if (timer) {
      clearTimeout(timer);
      timer = null;
    }
  };
  return throttled;
}

/** Check if map region moved enough to refetch (~110m default) */
export function hasRegionChanged(
  prev: { latitude: number; longitude: number } | null,
  next: { latitude: number; longitude: number },
  threshold: number = 0.001,
): boolean {
  if (!prev) return true;
  return (
    Math.abs(prev.latitude - next.latitude) > threshold ||
    Math.abs(prev.longitude - next.longitude) > threshold
  );
}

/** Haversine distance in meters */
export function haversineDistance(
  lat1: number,
  lng1: number,
  lat2: number,
  lng2: number,
): number {
  const R = 6371e3;
  const toRad = (d: number) => (d * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLng = toRad(lng2 - lng1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLng / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

/** Format: 42m, 150m, 1.2km */
export function formatDistance(meters: number): string {
  if (meters < 1000) return `${Math.round(meters)}m`;
  return `${(meters / 1000).toFixed(1)}km`;
}

/** Format: 0.05 km², 1.23 km² */
export function formatArea(sqMeters: number): string {
  const km2 = sqMeters / 1_000_000;
  return km2 < 0.01 ? `${Math.round(sqMeters)} m²` : `${km2.toFixed(2)} km²`;
}
