/**
 * LAYERS — CachedImage
 * ==========================================
 * Thin wrapper around expo-image. ONE place that decides caching policy,
 * placeholders, and transitions — so avatars and photo artifacts don't
 * re-download on every mount, and future tweaks touch one file.
 *
 * Requires:  npx expo install expo-image
 *
 * WHY expo-image over RN core <Image>:
 *   - Disk + memory cache out of the box (cachePolicy)
 *   - Blurhash/thumbhash placeholders
 *   - Priority hints, smooth crossfade transitions
 *
 * USAGE:
 *   <CachedImage uri={user.avatar_url} style={styles.avatar} />
 *   <CachedImage uri={payload.url} style={styles.photo} priority="high" />
 */

import React from "react";
import { StyleProp, ImageStyle } from "react-native";
import { Image } from "expo-image";

// A soft neutral blurhash so loading images shimmer instead of popping.
const DEFAULT_PLACEHOLDER = { blurhash: "L6PZfSi_.AyE_3t7t7R**0o#DgR4" };

interface Props {
  uri: string | null | undefined;
  style?: StyleProp<ImageStyle>;
  /** "low" for offscreen thumbnails, "high" for hero/detail images. */
  priority?: "low" | "normal" | "high";
  contentFit?: "cover" | "contain" | "fill";
  /** Crossfade duration ms. 0 to disable. */
  transition?: number;
  accessibilityLabel?: string;
  onError?: () => void;
}

function CachedImageBase({
  uri,
  style,
  priority = "normal",
  contentFit = "cover",
  transition = 200,
  accessibilityLabel,
  onError,
}: Props) {
  if (!uri) return null;

  return (
    <Image
      source={{ uri }}
      style={style}
      contentFit={contentFit}
      transition={transition}
      priority={priority}
      cachePolicy="memory-disk"
      placeholder={DEFAULT_PLACEHOLDER}
      accessibilityLabel={accessibilityLabel}
      onError={onError}
    />
  );
}

// Memo — avatars render inside FlatList rows everywhere.
export const CachedImage = React.memo(CachedImageBase);
export default CachedImage;
