/**
 * LAYERS — EditProfileModal Component
 * ==========================================
 * Bottom-sheet-style modal for editing profile.
 *
 * Fields: username, bio, avatar (via expo-image-picker).
 * Validates username availability before save.
 * Provides real-time character count and error messages.
 *
 * Note: Avatar upload requires expo-image-picker. If not available, shows alert.
 */

import React, { useState, useCallback } from "react";
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  Modal,
  StyleSheet,
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  Image,
} from "react-native";
import { Colors } from "../../constants/colors";
import { useAuthStore } from "../../store/authStore";
import { profileService, UpdateProfileRequest } from "../../services/profile";
import { authService } from "../../services/auth";
import { User } from "../../types";

interface EditProfileModalProps {
  visible: boolean;
  onClose: () => void;
  user: User;
  onSaved: (updatedUser: User) => void;
}

export default function EditProfileModal({
  visible,
  onClose,
  user,
  onSaved,
}: EditProfileModalProps) {
  const layer = useAuthStore((s) => s.layer);
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];

  // Form state
  const [username, setUsername] = useState(user.username || "");
  const [bio, setBio] = useState(user.bio || "");
  const [localAvatarUri, setLocalAvatarUri] = useState<string | null>(user.avatar_url || null);
  const [isSaving, setIsSaving] = useState(false);
  const [errors, setErrors] = useState<{ username?: string; bio?: string }>({});

  // ========================================================
  // VALIDATION
  // ========================================================

  const validate = useCallback((): boolean => {
    const newErrors: typeof errors = {};

    if (username.length < 3) {
      newErrors.username = "Username must be at least 3 characters";
    } else if (username.length > 50) {
      newErrors.username = "Username must be under 50 characters";
    } else if (!/^[a-zA-Z0-9_]+$/.test(username)) {
      newErrors.username = "Only letters, numbers, and underscores";
    }

    if (bio.length > 500) {
      newErrors.bio = `${bio.length}/500 characters`;
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  }, [username, bio]);

  // ========================================================
  // SAVE
  // ========================================================

  const handleSave = useCallback(async () => {
    if (!validate()) return;

    setIsSaving(true);
    try {
      const updates: UpdateProfileRequest = {};

      if (username !== user.username) {
        const { available } = await authService.checkUsername(username);
        if (!available) {
          setErrors((e) => ({ ...e, username: "Username already taken" }));
          setIsSaving(false);
          return;
        }
        updates.username = username;
      }

      if (bio !== (user.bio || "")) {
        updates.bio = bio;
      }

      if (Object.keys(updates).length === 0) {
        onClose();
        return;
      }

      const updatedUser = await profileService.updateProfile(updates);
      onSaved(updatedUser);
      onClose();
    } catch (error: any) {
      const message =
        error?.response?.data?.detail || "Failed to update profile";
      Alert.alert("Error", message);
    } finally {
      setIsSaving(false);
    }
  }, [username, bio, user, validate, onSaved, onClose]);

  // ========================================================
  // PICK AVATAR
  // ========================================================

  const handlePickAvatar = useCallback(async () => {
    // expo-image-picker integration
    try {
      const ImagePicker = require("expo-image-picker");
      const permission =
        await ImagePicker.requestMediaLibraryPermissionsAsync();
      if (!permission.granted) {
        Alert.alert(
          "Permission needed",
          "Allow LAYERS to access your photos to set an avatar.",
        );
        return;
      }

      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ["images"],
        allowsEditing: true,
        aspect: [1, 1],
        quality: 0.8,
      });

      if (!result.canceled && result.assets[0]) {
        const pickedUri = result.assets[0].uri;
        setLocalAvatarUri(pickedUri);
        setIsSaving(true);
        const avatarUrl = await profileService.uploadAvatar(pickedUri);
        const updatedUser = await profileService.updateProfile({
          avatar_url: avatarUrl,
        });
        onSaved(updatedUser);
        setIsSaving(false);
      }
    } catch (error) {
      console.warn("Image picker not available:", error);
      Alert.alert(
        "Coming soon",
        "Avatar upload requires expo-image-picker.\nRun: npx expo install expo-image-picker",
      );
      setIsSaving(false);
    }
  }, [onSaved]);

  // ========================================================
  // RENDER
  // ========================================================

  return (
    <Modal
      visible={visible}
      animationType="slide"
      transparent
      onRequestClose={onClose}
    >
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        style={styles.overlay}
      >
        <View style={[styles.sheet, { backgroundColor: colors.background }]}>
          {/* Handle bar */}
          <View style={[styles.handle, { backgroundColor: colors.border }]} />

          {/* Header */}
          <View style={styles.header}>
            <TouchableOpacity onPress={onClose}>
              <Text
                style={[styles.cancelText, { color: colors.textSecondary }]}
              >
                Cancel
              </Text>
            </TouchableOpacity>
            <Text style={[styles.title, { color: colors.text }]}>
              Edit Profile
            </Text>
            <TouchableOpacity onPress={handleSave} disabled={isSaving}>
              {isSaving ? (
                <ActivityIndicator size="small" color={colors.primary} />
              ) : (
                <Text style={[styles.saveText, { color: colors.primary }]}>
                  Save
                </Text>
              )}
            </TouchableOpacity>
          </View>

          <ScrollView showsVerticalScrollIndicator={false}>
            {/* Avatar */}
            <TouchableOpacity
              onPress={handlePickAvatar}
              style={styles.avatarSection}
              activeOpacity={0.7}
            >
              {localAvatarUri ? (
                <Image
                  source={{ uri: localAvatarUri }}
                  style={[styles.avatarCircle, { borderColor: colors.primary }]}
                />
              ) : (
                <View
                  style={[
                    styles.avatarCircle,
                    { backgroundColor: colors.primary },
                  ]}
                >
                  <Text style={styles.avatarInitial}>
                    {(username[0] || "?").toUpperCase()}
                  </Text>
                </View>
              )}
              <Text
                style={[styles.changeAvatarText, { color: colors.primary }]}
              >
                Change Photo
              </Text>
            </TouchableOpacity>

            {/* Username */}
            <View style={styles.field}>
              <Text
                style={[styles.fieldLabel, { color: colors.textSecondary }]}
              >
                Username
              </Text>
              <TextInput
                value={username}
                onChangeText={(text) => {
                  setUsername(text.toLowerCase().replace(/[^a-z0-9_]/g, ""));
                  setErrors((e) => ({ ...e, username: undefined }));
                }}
                style={[
                  styles.input,
                  {
                    color: colors.text,
                    backgroundColor: colors.surface,
                    borderColor: errors.username ? "#EF4444" : colors.border,
                  },
                ]}
                placeholder="your_username"
                placeholderTextColor={colors.textSecondary + "80"}
                autoCapitalize="none"
                autoCorrect={false}
                maxLength={50}
              />
              {errors.username && (
                <Text style={styles.errorText}>{errors.username}</Text>
              )}
              <Text style={[styles.charCount, { color: colors.textSecondary }]}>
                {username.length}/50
              </Text>
            </View>

            {/* Bio */}
            <View style={styles.field}>
              <Text
                style={[styles.fieldLabel, { color: colors.textSecondary }]}
              >
                Bio
              </Text>
              <TextInput
                value={bio}
                onChangeText={(text) => {
                  setBio(text);
                  setErrors((e) => ({ ...e, bio: undefined }));
                }}
                style={[
                  styles.textArea,
                  {
                    color: colors.text,
                    backgroundColor: colors.surface,
                    borderColor: errors.bio ? "#EF4444" : colors.border,
                  },
                ]}
                placeholder="Tell the city about yourself..."
                placeholderTextColor={colors.textSecondary + "80"}
                multiline
                numberOfLines={4}
                textAlignVertical="top"
                maxLength={500}
              />
              {errors.bio && <Text style={styles.errorText}>{errors.bio}</Text>}
              <Text style={[styles.charCount, { color: colors.textSecondary }]}>
                {bio.length}/500
              </Text>
            </View>
          </ScrollView>
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}

// ============================================================
// STYLES
// ============================================================

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    justifyContent: "flex-end",
    backgroundColor: "rgba(0,0,0,0.4)",
  },
  sheet: {
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    paddingBottom: 40,
    maxHeight: "85%",
  },
  handle: {
    width: 40,
    height: 4,
    borderRadius: 2,
    alignSelf: "center",
    marginTop: 10,
    marginBottom: 10,
  },
  header: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    paddingHorizontal: 16,
    paddingBottom: 16,
    borderBottomWidth: 0.5,
    borderBottomColor: "rgba(0,0,0,0.1)",
  },
  cancelText: {
    fontSize: 15,
  },
  title: {
    fontSize: 17,
    fontWeight: "600",
  },
  saveText: {
    fontSize: 15,
    fontWeight: "600",
  },
  avatarSection: {
    alignItems: "center",
    paddingVertical: 20,
  },
  avatarCircle: {
    width: 80,
    height: 80,
    borderRadius: 40,
    borderWidth: 2,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 8,
  },
  avatarInitial: {
    color: "#FFFFFF",
    fontSize: 32,
    fontWeight: "700",
  },
  changeAvatarText: {
    fontSize: 14,
    fontWeight: "500",
  },
  field: {
    paddingHorizontal: 16,
    marginBottom: 20,
  },
  fieldLabel: {
    fontSize: 13,
    fontWeight: "500",
    marginBottom: 6,
  },
  input: {
    borderWidth: 1,
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 16,
  },
  textArea: {
    borderWidth: 1,
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 16,
    minHeight: 100,
  },
  charCount: {
    fontSize: 11,
    textAlign: "right",
    marginTop: 4,
  },
  errorText: {
    fontSize: 12,
    color: "#EF4444",
    marginTop: 4,
  },
});
