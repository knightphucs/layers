/**
 * LAYERS — BoostButton Component
 * ===============================================
 * A button to boost an artifact (📡). Drop into ArtifactDetailScreen.
 *
 * - Shows remaining daily quota
 * - Disabled while boosting / when quota exhausted
 * - Confirms success with a brief state change
 *
 * PATTERN: React.memo, Colors[layer] theming.
 */

import React, { useEffect, useState, useCallback } from "react";
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
} from "react-native";
import { Colors } from "../../constants/colors";
import { useAuthStore } from "../../store/authStore";
import { useSocialSparkStore } from "../../store/socialSparkStore";

interface BoostButtonProps {
  artifactId: string;
  /** Hide if the viewer is the artifact's author (can't boost your own). */
  isOwnArtifact?: boolean;
}

function BoostButtonComponent({ artifactId, isOwnArtifact }: BoostButtonProps) {
  const layer = useAuthStore((s) => s.layer);
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];

  const quota = useSocialSparkStore((s) => s.boostQuota);
  const isBoosting = useSocialSparkStore((s) => s.isBoosting);
  const fetchBoostQuota = useSocialSparkStore((s) => s.fetchBoostQuota);
  const boostArtifact = useSocialSparkStore((s) => s.boostArtifact);

  const [boosted, setBoosted] = useState(false);

  useEffect(() => {
    if (!quota) fetchBoostQuota();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const remaining = quota?.remaining ?? null;
  const noneLeft = remaining !== null && remaining <= 0;
  const disabled = isBoosting || boosted || noneLeft;

  const handlePress = useCallback(async () => {
    const ok = await boostArtifact(artifactId);
    if (ok) setBoosted(true);
  }, [artifactId, boostArtifact]);

  if (isOwnArtifact) return null;

  return (
    <View style={styles.container}>
      <TouchableOpacity
        onPress={handlePress}
        disabled={disabled}
        activeOpacity={0.7}
        style={[
          styles.button,
          {
            backgroundColor: boosted
              ? colors.surface
              : noneLeft
                ? colors.border
                : colors.primary,
          },
        ]}
      >
        {isBoosting ? (
          <ActivityIndicator size="small" color="#FFFFFF" />
        ) : (
          <Text
            style={[
              styles.label,
              { color: boosted ? colors.primary : "#FFFFFF" },
            ]}
          >
            {boosted ? "📡 Boosted!" : "📡 Boost this memory"}
          </Text>
        )}
      </TouchableOpacity>

      {remaining !== null && !boosted && (
        <Text style={[styles.quota, { color: colors.textSecondary }]}>
          {noneLeft
            ? "No boosts left today — refreshes at midnight"
            : `${remaining} boost${remaining === 1 ? "" : "s"} left today`}
        </Text>
      )}
      {boosted && (
        <Text style={[styles.quota, { color: colors.textSecondary }]}>
          Reaching explorers up to 2km away for 24h ✨
        </Text>
      )}
    </View>
  );
}

export const BoostButton = React.memo(BoostButtonComponent);
BoostButton.displayName = "BoostButton";

const styles = StyleSheet.create({
  container: {
    alignItems: "center",
    marginVertical: 8,
  },
  button: {
    paddingHorizontal: 20,
    paddingVertical: 12,
    borderRadius: 24,
    minWidth: 200,
    alignItems: "center",
  },
  label: {
    fontSize: 15,
    fontWeight: "600",
  },
  quota: {
    fontSize: 12,
    marginTop: 6,
  },
});

export default BoostButton;
