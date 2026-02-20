// ===========================================
// LAYERS Login Screen
// ===========================================

import React, { useState } from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  Alert,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { AuthStackParamList } from "../../types";
import { useAuthStore } from "../../store/authStore";
import { authService, getErrorMessage, isNetworkError } from "../../services";
import { Input, Button, Divider } from "../../components";
import { Colors } from "../../constants/colors";

type Props = {
  navigation: NativeStackNavigationProp<AuthStackParamList, "Login">;
};

export default function LoginScreen({ navigation }: Props) {
  // Form state
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<{ email?: string; password?: string }>(
    {},
  );

  // Store
  const { login, layer } = useAuthStore();
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];

  // Validation
  const validate = (): boolean => {
    const newErrors: { email?: string; password?: string } = {};

    if (!email.trim()) {
      newErrors.email = "Email is required";
    } else if (!/\S+@\S+\.\S+/.test(email)) {
      newErrors.email = "Please enter a valid email";
    }

    if (!password) {
      newErrors.password = "Password is required";
    } else if (password.length < 8) {
      newErrors.password = "Password must be at least 8 characters";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Handle login - REAL API CALL! 🚀
  const handleLogin = async () => {
    if (!validate()) return;

    setLoading(true);

    try {
      // Call real API
      const response = await authService.login({
        email: email.trim().toLowerCase(),
        password,
      });

      // Store user and tokens
      await login(response.user, {
        access_token: response.access_token,
        refresh_token: response.refresh_token,
        token_type: response.token_type,
      });

      // Navigation happens automatically via RootNavigator
      console.log("✅ Login successful!");
    } catch (error: any) {
      console.error("Login error:", error);

      // Handle different error types
      if (isNetworkError(error)) {
        Alert.alert(
          "Connection Error",
          "Unable to connect to server. Please check:\n\n" +
            "1. Your backend is running\n" +
            "2. You updated the API_URL in config.ts\n" +
            "3. Phone and computer are on same WiFi",
          [{ text: "OK" }],
        );
      } else {
        const message = getErrorMessage(error);
        Alert.alert("Login Failed", message);
      }
    } finally {
      setLoading(false);
    }
  };

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
          {/* Header */}
          <View style={styles.header}>
            <Text style={styles.logo}>🌆</Text>
            <Text style={[styles.title, { color: colors.text }]}>LAYERS</Text>
            <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
              See the hidden layers of your city
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
                if (errors.email) setErrors({ ...errors, email: undefined });
              }}
              error={errors.email}
              keyboardType="email-address"
              autoCapitalize="none"
              autoComplete="email"
              leftIcon="📧"
              editable={!loading}
            />

            <Input
              label="Password"
              placeholder="••••••••"
              value={password}
              onChangeText={(text) => {
                setPassword(text);
                if (errors.password)
                  setErrors({ ...errors, password: undefined });
              }}
              error={errors.password}
              secureTextEntry={!showPassword}
              autoComplete="password"
              leftIcon="🔒"
              rightIcon={showPassword ? "👁️" : "👁️‍🗨️"}
              onRightIconPress={() => setShowPassword(!showPassword)}
              editable={!loading}
            />

            {/* Forgot Password */}
            <TouchableOpacity
              onPress={() => navigation.navigate("ForgotPassword")}
              style={styles.forgotLink}
              disabled={loading}
            >
              <Text style={[styles.forgotText, { color: colors.primary }]}>
                Forgot password?
              </Text>
            </TouchableOpacity>

            {/* Login Button */}
            <Button
              title="Sign In"
              onPress={handleLogin}
              loading={loading}
              icon="🚀"
            />

            {/* Divider */}
            <Divider text="or continue with" />

            {/* Social Login (placeholder) */}
            <View style={styles.socialRow}>
              <Button
                title="Google"
                onPress={() =>
                  Alert.alert(
                    "Coming Soon",
                    "Google login will be added in a future update!",
                  )
                }
                variant="outline"
                icon="🔷"
                style={styles.socialButton}
                disabled={loading}
              />
              <Button
                title="Apple"
                onPress={() =>
                  Alert.alert(
                    "Coming Soon",
                    "Apple login will be added in a future update!",
                  )
                }
                variant="outline"
                icon="🍎"
                style={styles.socialButton}
                disabled={loading}
              />
            </View>
          </View>

          {/* Footer */}
          <View style={styles.footer}>
            <Text style={[styles.footerText, { color: colors.textSecondary }]}>
              Don't have an account?{" "}
            </Text>
            <TouchableOpacity
              onPress={() => navigation.navigate("Register")}
              disabled={loading}
            >
              <Text style={[styles.linkText, { color: colors.primary }]}>
                Sign Up
              </Text>
            </TouchableOpacity>
          </View>

          {/* API Connected Badge */}
          <View
            style={[
              styles.apiBadge,
              { backgroundColor: colors.success + "20" },
            ]}
          >
            <Text style={[styles.apiText, { color: colors.success }]}>
              ✅ Day 3: Connected to FastAPI Backend!
            </Text>
          </View>
        </ScrollView>
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
  scroll: {
    flexGrow: 1,
    paddingHorizontal: 24,
    paddingBottom: 24,
  },
  header: {
    alignItems: "center",
    marginTop: 40,
    marginBottom: 40,
  },
  logo: {
    fontSize: 64,
    marginBottom: 12,
  },
  title: {
    fontSize: 36,
    fontWeight: "bold",
    letterSpacing: 4,
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 15,
    textAlign: "center",
  },
  form: {
    marginBottom: 24,
  },
  forgotLink: {
    alignSelf: "flex-end",
    marginBottom: 24,
    marginTop: -8,
  },
  forgotText: {
    fontSize: 14,
    fontWeight: "500",
  },
  socialRow: {
    flexDirection: "row",
    gap: 12,
  },
  socialButton: {
    flex: 1,
  },
  footer: {
    flexDirection: "row",
    justifyContent: "center",
    marginTop: 24,
  },
  footerText: {
    fontSize: 15,
  },
  linkText: {
    fontSize: 15,
    fontWeight: "600",
  },
  apiBadge: {
    marginTop: 32,
    padding: 12,
    borderRadius: 12,
    alignItems: "center",
  },
  apiText: {
    fontSize: 13,
    fontWeight: "500",
  },
});
