// ===========================================
// LAYERS Forgot Password Screen
// ===========================================

import React, { useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  KeyboardAvoidingView,
  Platform,
  Alert,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";
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

  // Handle submit - REAL API CALL! 🚀
  const handleSubmit = async () => {
    if (!validate()) return;

    setLoading(true);
    setError("");

    try {
      await authService.requestPasswordReset(email.trim().toLowerCase());
      setSent(true);
      console.log("✅ Password reset email sent!");
    } catch (err: any) {
      console.error("Password reset error:", err);

      if (isNetworkError(err)) {
        Alert.alert(
          "Connection Error",
          "Unable to connect to server. Please check your connection.",
          [{ text: "OK" }],
        );
      } else {
        // Note: For security, many backends return success even if email doesn't exist
        // We'll show success anyway to not leak information about registered emails
        const message = getErrorMessage(err);

        // If it's a "not found" error, still show success for security
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

  // Handle resend
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
      // Still show sent state for security
      setSent(true);
    } finally {
      setLoading(false);
    }
  };

  // Success state
  if (sent) {
    return (
      <SafeAreaView
        style={[styles.container, { backgroundColor: colors.background }]}
      >
        <View style={styles.content}>
          <Card variant="elevated" style={styles.successCard}>
            <Text style={styles.successIcon}>📧</Text>
            <Text style={[styles.successTitle, { color: colors.text }]}>
              Check your email
            </Text>
            <Text style={[styles.successText, { color: colors.textSecondary }]}>
              If an account exists for{"\n"}
              <Text style={{ fontWeight: "600", color: colors.text }}>
                {email}
              </Text>
              {"\n"}you'll receive a password reset link.
            </Text>

            <View style={styles.successButtons}>
              <Button
                title="Back to Login"
                onPress={() => navigation.navigate("Login")}
                icon="←"
              />
            </View>
          </Card>

          <Text style={[styles.resendText, { color: colors.textSecondary }]}>
            Didn't receive the email?{" "}
            <Text
              style={{ color: colors.primary, fontWeight: "500" }}
              onPress={handleResend}
            >
              Resend
            </Text>
          </Text>

          <View style={styles.helpSection}>
            <Text style={[styles.helpTitle, { color: colors.text }]}>
              📌 Check these first:
            </Text>
            <Text style={[styles.helpText, { color: colors.textSecondary }]}>
              • Check your spam/junk folder{"\n"}• Make sure you entered the
              correct email{"\n"}• The link expires in 1 hour
            </Text>
          </View>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView
      style={[styles.container, { backgroundColor: colors.background }]}
    >
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        style={styles.keyboard}
      >
        <View style={styles.content}>
          {/* Back Button */}
          <TouchableOpacity
            style={styles.backButton}
            onPress={() => navigation.goBack()}
            disabled={loading}
          >
            <Text style={[styles.backText, { color: colors.primary }]}>
              ← Back
            </Text>
          </TouchableOpacity>

          {/* Header */}
          <View style={styles.header}>
            <Text style={styles.logo}>🔑</Text>
            <Text style={[styles.title, { color: colors.text }]}>
              Reset Password
            </Text>
            <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
              Enter your email and we'll send you a link to reset your password
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
              leftIcon="📧"
              editable={!loading}
            />

            <Button
              title="Send Reset Link"
              onPress={handleSubmit}
              loading={loading}
              icon="✉️"
            />
          </View>

          {/* Help */}
          <Card variant="outlined" style={styles.helpCard}>
            <Text style={[styles.helpTitle, { color: colors.text }]}>
              💡 Need help?
            </Text>
            <Text style={[styles.helpText, { color: colors.textSecondary }]}>
              If you're having trouble accessing your account, please contact
              support at{" "}
              <Text style={{ color: colors.primary }}>support@layers.app</Text>
            </Text>
          </Card>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  keyboard: {
    flex: 1,
  },
  content: {
    flex: 1,
    paddingHorizontal: 24,
  },
  backButton: {
    marginTop: 16,
    marginBottom: 24,
  },
  backText: {
    fontSize: 16,
    fontWeight: "500",
  },
  header: {
    alignItems: "center",
    marginBottom: 40,
  },
  logo: {
    fontSize: 56,
    marginBottom: 16,
  },
  title: {
    fontSize: 28,
    fontWeight: "bold",
    marginBottom: 12,
  },
  subtitle: {
    fontSize: 15,
    textAlign: "center",
    lineHeight: 22,
    paddingHorizontal: 20,
  },
  form: {
    marginBottom: 32,
  },
  helpCard: {
    marginTop: "auto",
    marginBottom: 40,
  },
  helpTitle: {
    fontSize: 15,
    fontWeight: "600",
    marginBottom: 8,
  },
  helpText: {
    fontSize: 13,
    lineHeight: 20,
  },
  // Success state styles
  successCard: {
    alignItems: "center",
    marginTop: 80,
    padding: 32,
  },
  successIcon: {
    fontSize: 64,
    marginBottom: 24,
  },
  successTitle: {
    fontSize: 24,
    fontWeight: "bold",
    marginBottom: 12,
  },
  successText: {
    fontSize: 15,
    textAlign: "center",
    lineHeight: 24,
    marginBottom: 32,
  },
  successButtons: {
    width: "100%",
  },
  resendText: {
    textAlign: "center",
    marginTop: 24,
    fontSize: 14,
  },
  helpSection: {
    marginTop: 32,
    padding: 16,
    backgroundColor: "rgba(0,0,0,0.03)",
    borderRadius: 12,
  },
});
