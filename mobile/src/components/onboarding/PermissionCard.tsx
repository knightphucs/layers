/**
 * LAYERS — PermissionCard
 * ==========================================
 * A single permission row on the Permissions screen.
 *
 * STATES:
 *   unknown  → "Allow" button
 *   granted  → green check, card dims slightly
 *   denied   → "Open Settings" hint (required perms) / stays skippable
 */

import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { PermissionItem, PermissionStatus } from '../../types/onboarding';

interface Props {
    item: PermissionItem;
    status: PermissionStatus;
    onRequest: (item: PermissionItem) => void;
    colors: {
        surface: string;
        text: string;
        textSecondary: string;
        primary: string;
        border: string;
    };
}

function PermissionCard({ item, status, onRequest, colors }: Props) {
    const granted = status === 'granted';
    const denied = status === 'denied';

    return (
    <View
      style={[
        styles.card,
        {
          backgroundColor: colors.surface,
          borderColor: granted ? "#34D399" : colors.border,
          opacity: granted ? 0.85 : 1,
        },
      ]}
    >
      <Text style={styles.icon}>{item.icon}</Text>

      <View style={styles.content}>
        <View style={styles.titleRow}>
          <Text style={[styles.title, { color: colors.text }]}>
            {item.title}
          </Text>
          {!item.required && (
            <Text style={[styles.optional, { color: colors.textSecondary }]}>
              optional
            </Text>
          )}
        </View>
        <Text style={[styles.description, { color: colors.textSecondary }]}>
          {item.description}
        </Text>
        {denied && item.required && (
          <Text style={styles.deniedHint}>
            Permission denied — enable Location in your device Settings to
            play LAYERS.
          </Text>
        )}
      </View>

      {granted ? (
        <Text style={styles.grantedCheck}>✅</Text>
      ) : (
        <TouchableOpacity
          style={[styles.allowButton, { backgroundColor: colors.primary }]}
          onPress={() => onRequest(item)}
          accessibilityRole="button"
          accessibilityLabel={`Allow ${item.title}`}
        >
          <Text style={styles.allowText}>Allow</Text>
        </TouchableOpacity>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    flexDirection: "row",
    alignItems: "center",
    borderWidth: 1,
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
    gap: 12,
  },
  icon: {
    fontSize: 28,
  },
  content: {
    flex: 1,
  },
  titleRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginBottom: 4,
  },
  title: {
    fontSize: 16,
    fontWeight: "700",
  },
  optional: {
    fontSize: 11,
    fontStyle: "italic",
  },
  description: {
    fontSize: 13,
    lineHeight: 18,
  },
  deniedHint: {
    fontSize: 12,
    color: "#F87171",
    marginTop: 6,
  },
  grantedCheck: {
    fontSize: 20,
  },
  allowButton: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 20,
  },
  allowText: {
    color: "#FFFFFF",
    fontWeight: "700",
    fontSize: 13,
  },
});

export default React.memo(PermissionCard);