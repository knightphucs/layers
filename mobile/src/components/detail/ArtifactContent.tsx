/**
 * LAYERS - Artifact Content Renderer
 * ====================================
 *
 * Renders the UNLOCKED artifact content with style per type:
 *   ✉️ LETTER     — Handwritten-feel text on aged paper
 *   📓 NOTEBOOK   — Shared writing with page separators
 *   📸 PHOTO      — Image with caption (placeholder)
 *   🎤 VOICE      — Waveform with play button (placeholder)
 *   ✈️ PAPER_PLANE — Short message in folded paper style
 *   ⏰ TIME_CAPSULE — Sealed envelope with date
 *   🎁 VOUCHER    — Coupon card design
 */

import React, { memo } from "react";
import { View, Text, StyleSheet, Platform } from "react-native";

interface Props {
  contentType: string;
  payload: Record<string, any>;
  isShadow: boolean;
  creatorUsername?: string;
  createdAt?: string;
  viewCount?: number;
  replyCount?: number;
}

function ArtifactContentComponent({
  contentType,
  payload,
  isShadow,
  creatorUsername,
  createdAt,
  viewCount = 0,
  replyCount = 0,
}: Props) {
  const accent = isShadow ? "#8B5CF6" : "#3B82F6";
  const textColor = isShadow ? "#F3F4F6" : "#1F2937";
  const subtextColor = isShadow ? "#9CA3AF" : "#6B7280";
  const paperBg = isShadow
    ? "rgba(139, 92, 246, 0.06)"
    : "rgba(245, 240, 230, 0.8)";
  const borderColor = isShadow
    ? "rgba(139, 92, 246, 0.15)"
    : "rgba(180, 160, 130, 0.3)";

  // Format date
  const dateStr = createdAt
    ? new Date(createdAt).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    : "";

  // ---- LETTER ----
  if (contentType === "LETTER") {
    return (
      <View style={styles.contentContainer}>
        {/* Paper-like background */}
        <View style={[styles.paper, { backgroundColor: paperBg, borderColor }]}>
          {/* Decorative line at top */}
          <View style={[styles.paperLine, { backgroundColor: borderColor }]} />

          <Text style={[styles.letterText, { color: textColor }]}>
            {payload.text || ""}
          </Text>

          {/* Decorative line at bottom */}
          <View style={[styles.paperLine, { backgroundColor: borderColor }]} />
        </View>

        {/* Meta info */}
        <View style={styles.metaRow}>
          {creatorUsername && (
            <Text style={[styles.metaText, { color: subtextColor }]}>
              {isShadow ? "👻" : "✍️"} {creatorUsername}
            </Text>
          )}
          <Text style={[styles.metaText, { color: subtextColor }]}>
            {dateStr}
          </Text>
        </View>

        {/* Engagement stats */}
        <View style={styles.statsRow}>
          <Text style={[styles.statText, { color: subtextColor }]}>
            👁️ {viewCount} views
          </Text>
          <Text style={[styles.statText, { color: subtextColor }]}>
            💬 {replyCount} replies
          </Text>
        </View>
      </View>
    );
  }

  // ---- NOTEBOOK ----
  if (contentType === "NOTEBOOK") {
    const pages = payload.pages || [];
    return (
      <View style={styles.contentContainer}>
        <View
          style={[styles.notebook, { backgroundColor: paperBg, borderColor }]}
        >
          {/* Spiral binding visual */}
          <View style={styles.spiralBinding}>
            {[0, 1, 2, 3, 4].map((i) => (
              <View
                key={i}
                style={[
                  styles.spiralRing,
                  { borderColor: subtextColor + "40" },
                ]}
              />
            ))}
          </View>

          {pages.length > 0 ? (
            pages.map((page: string, idx: number) => (
              <View key={idx}>
                <Text style={[styles.notebookText, { color: textColor }]}>
                  {page}
                </Text>
                {idx < pages.length - 1 && (
                  <View
                    style={[
                      styles.pageDivider,
                      { backgroundColor: borderColor },
                    ]}
                  />
                )}
              </View>
            ))
          ) : (
            <Text style={[styles.emptyText, { color: subtextColor }]}>
              Empty notebook — be the first to write!
            </Text>
          )}
        </View>

        <View style={styles.metaRow}>
          <Text style={[styles.metaText, { color: subtextColor }]}>
            📓 {pages.length} page{pages.length !== 1 ? "s" : ""}
          </Text>
          <Text style={[styles.metaText, { color: subtextColor }]}>
            {dateStr}
          </Text>
        </View>
      </View>
    );
  }

  // ---- PAPER PLANE ----
  if (contentType === "PAPER_PLANE") {
    return (
      <View style={styles.contentContainer}>
        <View
          style={[styles.planeCard, { backgroundColor: paperBg, borderColor }]}
        >
          <Text style={styles.planeEmoji}>✈️</Text>
          <Text style={[styles.planeText, { color: textColor }]}>
            {payload.text || ""}
          </Text>
          {payload.flight_distance && (
            <Text style={[styles.planeDistance, { color: accent }]}>
              Flew {Math.round(payload.flight_distance)}m to land here
            </Text>
          )}
        </View>
      </View>
    );
  }

  // ---- TIME CAPSULE ----
  if (contentType === "TIME_CAPSULE") {
    return (
      <View style={styles.contentContainer}>
        <View
          style={[
            styles.capsuleCard,
            { backgroundColor: paperBg, borderColor },
          ]}
        >
          <Text style={styles.capsuleEmoji}>⏰</Text>
          <Text style={[styles.letterText, { color: textColor }]}>
            {payload.text || ""}
          </Text>
          {payload.media_url && (
            <Text style={[styles.metaText, { color: subtextColor }]}>
              📎 Media attached
            </Text>
          )}
        </View>
        <View style={styles.metaRow}>
          <Text style={[styles.metaText, { color: subtextColor }]}>
            ⏰ Opened from the past
          </Text>
          <Text style={[styles.metaText, { color: subtextColor }]}>
            {dateStr}
          </Text>
        </View>
      </View>
    );
  }

  // ---- VOUCHER ----
  if (contentType === "VOUCHER") {
    return (
      <View style={styles.contentContainer}>
        <View style={[styles.voucherCard, { borderColor: accent }]}>
          <Text style={styles.voucherEmoji}>🎁</Text>
          <Text style={[styles.voucherCode, { color: accent }]}>
            {payload.code || "CODE"}
          </Text>
          {payload.discount && (
            <Text style={[styles.voucherDiscount, { color: textColor }]}>
              {payload.discount}% OFF
            </Text>
          )}
          {payload.expiry && (
            <Text style={[styles.metaText, { color: subtextColor }]}>
              Expires: {payload.expiry}
            </Text>
          )}
        </View>
      </View>
    );
  }

  // ---- PHOTO / VOICE placeholders ----
  return (
    <View style={styles.contentContainer}>
      <View style={[styles.paper, { backgroundColor: paperBg, borderColor }]}>
        <Text style={[styles.placeholderText, { color: subtextColor }]}>
          {contentType === "PHOTO"
            ? "📸 Photo content (Week 5)"
            : "🎤 Voice note (Week 5)"}
        </Text>
        {payload.caption && (
          <Text style={[styles.letterText, { color: textColor, marginTop: 8 }]}>
            {payload.caption}
          </Text>
        )}
        {payload.transcript && (
          <Text style={[styles.letterText, { color: textColor, marginTop: 8 }]}>
            {payload.transcript}
          </Text>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  contentContainer: { paddingVertical: 8 },

  // Paper/Letter
  paper: {
    borderRadius: 16,
    borderWidth: 1,
    padding: 20,
    marginBottom: 12,
  },
  paperLine: { height: 1, marginBottom: 12 },
  letterText: {
    fontSize: 16,
    lineHeight: 26,
    fontStyle: "italic",
  },

  // Notebook
  notebook: {
    borderRadius: 16,
    borderWidth: 1,
    padding: 20,
    paddingLeft: 36,
    marginBottom: 12,
  },
  spiralBinding: {
    position: "absolute",
    left: 18,
    top: 16,
    bottom: 16,
    justifyContent: "space-evenly",
  },
  spiralRing: { width: 10, height: 10, borderRadius: 5, borderWidth: 1.5 },
  notebookText: { fontSize: 15, lineHeight: 24, marginBottom: 8 },
  pageDivider: { height: 1, marginVertical: 12 },
  emptyText: {
    fontSize: 14,
    fontStyle: "italic",
    textAlign: "center",
    paddingVertical: 20,
  },

  // Paper Plane
  planeCard: {
    borderRadius: 16,
    borderWidth: 1,
    padding: 20,
    alignItems: "center",
    marginBottom: 12,
  },
  planeEmoji: { fontSize: 36, marginBottom: 8 },
  planeText: { fontSize: 16, lineHeight: 24, textAlign: "center" },
  planeDistance: { fontSize: 12, fontWeight: "600", marginTop: 8 },

  // Time Capsule
  capsuleCard: {
    borderRadius: 16,
    borderWidth: 1,
    padding: 20,
    alignItems: "center",
    marginBottom: 12,
  },
  capsuleEmoji: { fontSize: 36, marginBottom: 10 },

  // Voucher
  voucherCard: {
    borderRadius: 16,
    borderWidth: 2,
    borderStyle: "dashed",
    padding: 24,
    alignItems: "center",
    marginBottom: 12,
  },
  voucherEmoji: { fontSize: 36, marginBottom: 8 },
  voucherCode: {
    fontSize: 24,
    fontWeight: "900",
    letterSpacing: 3,
    marginBottom: 4,
  },
  voucherDiscount: { fontSize: 18, fontWeight: "700" },

  // Meta
  metaRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    marginBottom: 4,
  },
  metaText: { fontSize: 12 },
  statsRow: { flexDirection: "row", gap: 16, marginTop: 4 },
  statText: { fontSize: 12 },
  placeholderText: { fontSize: 14, textAlign: "center", paddingVertical: 30 },
});

export default memo(ArtifactContentComponent);
