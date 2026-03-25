import React, { useState, useEffect, useRef } from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  KeyboardAvoidingView,
  Platform,
  Alert,
  ScrollView,
  Animated,
  Easing,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { Ionicons } from "@expo/vector-icons";

import { AuthStackParamList } from "../../types";
import { useAuthStore } from "../../store/authStore";
import { authService, getErrorMessage, isNetworkError } from "../../services";
import { Input, Button, Card } from "../../components";
import { Colors } from "../../constants/colors";

type Props = {
  navigation: NativeStackNavigationProp<AuthStackParamList, "ForgotPassword">;
};

export default function ForgotPasswordScreen({ navigation }: Props) {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");

  const { layer } = useAuthStore();
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];

  // -----------------------------------------------------------------
  // Animation setup: Snappy "Pop & Rest" Logo
  // -----------------------------------------------------------------
  const progress = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.loop(
      Animated.sequence([
        Animated.timing(progress, {
          toValue: 1,
          duration: 1200,
          easing: Easing.inOut(Easing.quad),
          useNativeDriver: true,
        }),
        Animated.timing(progress, {
          toValue: 0,
          duration: 1200,
          easing: Easing.inOut(Easing.quad),
          useNativeDriver: true,
        }),
      ]),
    ).start();
  }, [progress]);

  const Y1 = progress.interpolate({ inputRange: [0, 1], outputRange: [8, 16] });
  const Y2 = progress.interpolate({ inputRange: [0, 1], outputRange: [0, 0] });
  const Y3 = progress.interpolate({
    inputRange: [0, 1],
    outputRange: [-8, -16],
  });

  const validate = (): boolean => {
    if (!email.trim()) {
      setError("Email is required");
      return false;
    }
    if (!/\S+@\S+\.\S+/.test(email)) {
      setError("Please enter a valid email");
      return false;
    }
    return true;
  };

  const handleSubmit = async () => {
    if (!validate()) return;

    setLoading(true);
    setError("");

    try {
      await authService.requestPasswordReset(email.trim().toLowerCase());
      setSent(true);
    } catch (err: any) {
      if (isNetworkError(err)) {
        Alert.alert(
          "Connection Error",
          "Unable to connect to server. Please check your connection.",
          [{ text: "OK" }],
        );
      } else {
        // For security, many backends return success even if email doesn't exist
        const message = getErrorMessage(err);
        if (err.response?.status === 404) {
          setSent(true);
        } else {
          setError(message);
        }
      }
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    setSent(false);
    setLoading(true);

    try {
      await authService.requestPasswordReset(email.trim().toLowerCase());
      setSent(true);
      Alert.alert(
        "Email Sent!",
        "We've sent another reset link to your email.",
      );
    } catch (err) {
      setSent(true);
    } finally {
      setLoading(false);
    }
  };

  // -----------------------------------------------------------------
  // Success State View
  // -----------------------------------------------------------------
  if (sent) {
    return (
      <SafeAreaView
        style={[styles.container, { backgroundColor: colors.background }]}
      >
        <ScrollView contentContainerStyle={styles.scroll}>
          <Card variant="elevated" style={styles.successCard}>
            <Ionicons
              name="mail-unread-outline"
              size={64}
              color={colors.primary}
              style={styles.successIcon}
            />
            <Text style={[styles.successTitle, { color: colors.text }]}>
              Check your email
            </Text>
            <Text style={[styles.successText, { color: colors.textSecondary }]}>
              If an account exists for{"\n"}
              <Text style={{ fontWeight: "700", color: colors.text }}>
                {email}
              </Text>
              {"\n"}you'll receive a password reset link.
            </Text>

            <View style={styles.successButtons}>
              <Button
                title="Back to Login"
                onPress={() => navigation.navigate("Login")}
              />
            </View>
          </Card>

          <Text style={[styles.resendText, { color: colors.textSecondary }]}>
            Didn't receive the email?{" "}
            <Text
              style={{ color: colors.primary, fontWeight: "700" }}
              onPress={handleResend}
            >
              Resend
            </Text>
          </Text>

          <View
            style={[
              styles.helpSection,
              { backgroundColor: colors.border + "40" },
            ]}
          >
            <View style={styles.helpHeaderRow}>
              <Ionicons
                name="information-circle-outline"
                size={20}
                color={colors.text}
              />
              <Text style={[styles.helpTitle, { color: colors.text }]}>
                Check these first:
              </Text>
            </View>
            <Text style={[styles.helpText, { color: colors.textSecondary }]}>
              • Check your spam or junk folder{"\n"}• Make sure you entered the
              correct email{"\n"}• The reset link expires in 1 hour
            </Text>
          </View>
        </ScrollView>
      </SafeAreaView>
    );
  }

  // -----------------------------------------------------------------
  // Default Input View
  // -----------------------------------------------------------------
  return (
    <SafeAreaView
      style={[styles.container, { backgroundColor: colors.background }]}
    >
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        style={styles.keyboard}
      >
        <ScrollView
          contentContainerStyle={styles.scroll}
          keyboardShouldPersistTaps="handled"
          showsVerticalScrollIndicator={false}
        >
          {/* Back Button */}
          <TouchableOpacity
            style={styles.backButton}
            onPress={() => navigation.goBack()}
            disabled={loading}
          >
            <Ionicons name="arrow-back" size={20} color={colors.primary} />
            <Text style={[styles.backText, { color: colors.primary }]}>
              Back
            </Text>
          </TouchableOpacity>

          {/* Header */}
          <View style={styles.header}>
            <View
              style={[
                styles.logoContainer,
                { backgroundColor: colors.primary + "15" },
              ]}
            >
              <Animated.View
                style={[
                  styles.customLayer,
                  {
                    backgroundColor: colors.primary,
                    borderColor: colors.background,
                    opacity: 0.3,
                    transform: [
                      { translateY: Y1 },
                      { rotateX: "65deg" },
                      { rotateZ: "45deg" },
                    ],
                  },
                ]}
              />
              <Animated.View
                style={[
                  styles.customLayer,
                  {
                    backgroundColor: colors.primary,
                    borderColor: colors.background,
                    opacity: 0.7,
                    transform: [
                      { translateY: Y2 },
                      { rotateX: "65deg" },
                      { rotateZ: "45deg" },
                    ],
                  },
                ]}
              />
              <Animated.View
                style={[
                  styles.customLayer,
                  {
                    backgroundColor: colors.primary,
                    borderColor: colors.background,
                    opacity: 1.0,
                    transform: [
                      { translateY: Y3 },
                      { rotateX: "65deg" },
                      { rotateZ: "45deg" },
                    ],
                  },
                ]}
              />
            </View>

            <Text style={[styles.title, { color: colors.text }]}>RECOVERY</Text>
            <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
              Enter your email to receive a reset link
            </Text>
          </View>

          {/* Form */}
          <View style={styles.form}>
            <Input
              label="Email"
              placeholder="your@email.com"
              value={email}
              onChangeText={(text) => {
                setEmail(text);
                setError("");
              }}
              error={error}
              keyboardType="email-address"
              autoCapitalize="none"
              autoComplete="email"
              leftIcon={
                <Ionicons
                  name="mail-outline"
                  size={20}
                  color={colors.textSecondary}
                />
              }
              editable={!loading}
            />

            <View style={styles.buttonContainer}>
              <Button
                title="Send Reset Link"
                onPress={handleSubmit}
                loading={loading}
              />
            </View>
          </View>

          {/* Help */}
          <Card variant="outlined" style={styles.helpCard}>
            <View style={styles.helpHeaderRow}>
              <Ionicons
                name="help-buoy-outline"
                size={20}
                color={colors.text}
              />
              <Text style={[styles.helpTitle, { color: colors.text }]}>
                Need help?
              </Text>
            </View>
            <Text style={[styles.helpText, { color: colors.textSecondary }]}>
              If you're having trouble accessing your account, please contact
              support at{" "}
              <Text style={{ color: colors.primary, fontWeight: "600" }}>
                support@layers.app
              </Text>
            </Text>
          </Card>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  keyboard: { flex: 1 },
  scroll: {
    flexGrow: 1,
    paddingHorizontal: 28, // Matched Login
    paddingBottom: 40,
    justifyContent: "center",
  },
  backButton: {
    flexDirection: "row",
    alignItems: "center",
    alignSelf: "flex-start",
    marginTop: 16,
    marginBottom: 24,
    paddingVertical: 8,
    paddingRight: 16,
    gap: 4,
  },
  backText: { fontSize: 16, fontWeight: "600" },
  header: { alignItems: "center", marginBottom: 40 },
  logoContainer: {
    width: 96,
    height: 96,
    borderRadius: 28,
    justifyContent: "center",
    alignItems: "center",
    marginBottom: 24,
    position: "relative",
  },
  customLayer: {
    position: "absolute",
    width: 44,
    height: 44,
    borderRadius: 6,
    borderWidth: 2.5,
  },
  title: { fontSize: 32, fontWeight: "800", letterSpacing: 2, marginBottom: 8 }, // Matched Login
  subtitle: { fontSize: 16, textAlign: "center", opacity: 0.8 }, // Matched Login
  form: { marginBottom: 32 },
  buttonContainer: {
    marginTop: 8,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 12,
    elevation: 4, // Matched Login
  },
  helpCard: { marginTop: "auto", marginBottom: 20 },
  helpHeaderRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 8,
    gap: 8,
  },
  helpTitle: { fontSize: 16, fontWeight: "700" },
  helpText: { fontSize: 14, lineHeight: 22 },

  // Success state styles
  successCard: {
    alignItems: "center",
    marginTop: 60,
    padding: 32,
  },
  successIcon: { marginBottom: 24 },
  successTitle: { fontSize: 28, fontWeight: "800", marginBottom: 12 },
  successText: {
    fontSize: 16,
    textAlign: "center",
    lineHeight: 24,
    marginBottom: 32,
  },
  successButtons: { width: "100%", marginTop: 8 },
  resendText: { textAlign: "center", marginTop: 24, fontSize: 15 },
  helpSection: {
    marginTop: 40,
    padding: 20,
    borderRadius: 16,
  },
});
