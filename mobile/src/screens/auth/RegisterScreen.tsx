// ===========================================
// LAYERS Register Screen
// ===========================================

import React, { useState, useCallback, useRef } from "react";
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
  navigation: NativeStackNavigationProp<AuthStackParamList, "Register">;
};

// Debounce helper
const useDebounce = () => {
  const timeoutRef = useRef<NodeJS.Timeout | undefined>(undefined);

  return useCallback((callback: () => void, delay: number) => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    timeoutRef.current = setTimeout(callback, delay);
  }, []);
};

export default function RegisterScreen({ navigation }: Props) {
  // Form state
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);

  // Availability state
  const [checkingUsername, setCheckingUsername] = useState(false);
  const [checkingEmail, setCheckingEmail] = useState(false);
  const [usernameAvailable, setUsernameAvailable] = useState<boolean | null>(
    null,
  );
  const [emailAvailable, setEmailAvailable] = useState<boolean | null>(null);

  const [errors, setErrors] = useState<{
    username?: string;
    email?: string;
    password?: string;
    confirmPassword?: string;
  }>({});

  // Store
  const { login, layer } = useAuthStore();
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];
  const debounce = useDebounce();

  // Check username availability
  const checkUsernameAvailability = async (value: string) => {
    if (value.length < 3) {
      setUsernameAvailable(null);
      return;
    }

    setCheckingUsername(true);
    try {
      const result = await authService.checkUsername(value);
      setUsernameAvailable(result.available);
      if (!result.available) {
        setErrors((prev) => ({
          ...prev,
          username: "Username is already taken",
        }));
      }
    } catch (error) {
      console.log("Username check failed:", error);
    } finally {
      setCheckingUsername(false);
    }
  };

  // Check email availability
  const checkEmailAvailability = async (value: string) => {
    if (!/\S+@\S+\.\S+/.test(value)) {
      setEmailAvailable(null);
      return;
    }

    setCheckingEmail(true);
    try {
      const result = await authService.checkEmail(value);
      setEmailAvailable(result.available);
      if (!result.available) {
        setErrors((prev) => ({
          ...prev,
          email: "Email is already registered",
        }));
      }
    } catch (error) {
      console.log("Email check failed:", error);
    } finally {
      setCheckingEmail(false);
    }
  };

  // Handle username change with debounced check
  const handleUsernameChange = (text: string) => {
    const cleaned = text.toLowerCase().replace(/[^a-z0-9_]/g, "");
    setUsername(cleaned);
    setUsernameAvailable(null);
    clearError("username");

    if (cleaned.length >= 3) {
      debounce(() => checkUsernameAvailability(cleaned), 500);
    }
  };

  // Handle email change with debounced check
  const handleEmailChange = (text: string) => {
    setEmail(text);
    setEmailAvailable(null);
    clearError("email");

    if (/\S+@\S+\.\S+/.test(text)) {
      debounce(() => checkEmailAvailability(text), 500);
    }
  };

  // Validation
  const validate = (): boolean => {
    const newErrors: typeof errors = {};

    // Username validation
    if (!username.trim()) {
      newErrors.username = "Username is required";
    } else if (username.length < 3) {
      newErrors.username = "Username must be at least 3 characters";
    } else if (!/^[a-zA-Z0-9_]+$/.test(username)) {
      newErrors.username =
        "Username can only contain letters, numbers, and underscores";
    } else if (usernameAvailable === false) {
      newErrors.username = "Username is already taken";
    }

    // Email validation
    if (!email.trim()) {
      newErrors.email = "Email is required";
    } else if (!/\S+@\S+\.\S+/.test(email)) {
      newErrors.email = "Please enter a valid email";
    } else if (emailAvailable === false) {
      newErrors.email = "Email is already registered";
    }

    // Password validation
    if (!password) {
      newErrors.password = "Password is required";
    } else if (password.length < 8) {
      newErrors.password = "Password must be at least 8 characters";
    } else if (!/(?=.*[0-9])/.test(password)) {
      newErrors.password = "Password must contain at least one number";
    }

    // Confirm password
    if (!confirmPassword) {
      newErrors.confirmPassword = "Please confirm your password";
    } else if (password !== confirmPassword) {
      newErrors.confirmPassword = "Passwords do not match";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  // Clear error on input change
  const clearError = (field: keyof typeof errors) => {
    if (errors[field]) {
      setErrors({ ...errors, [field]: undefined });
    }
  };

  // Handle register - REAL API CALL! 🚀
  const handleRegister = async () => {
    if (!validate()) return;

    setLoading(true);

    try {
      // Call real API
      const response = await authService.register({
        email: email.trim().toLowerCase(),
        username: username.trim().toLowerCase(),
        password,
      });

      // Store user and tokens
      await login(response.user, {
        access_token: response.access_token,
        refresh_token: response.refresh_token,
        token_type: response.token_type,
      });

      console.log("✅ Registration successful!");

      // Show welcome message
      Alert.alert(
        "Welcome to LAYERS! 🌆",
        `Your account has been created successfully, ${response.user.username}!`,
        [{ text: "Start Exploring!" }],
      );
    } catch (error: any) {
      console.error("Registration error:", error);

      if (isNetworkError(error)) {
        Alert.alert(
          "Connection Error",
          "Unable to connect to server. Please check your connection and try again.",
          [{ text: "OK" }],
        );
      } else {
        const message = getErrorMessage(error);
        Alert.alert("Registration Failed", message);
      }
    } finally {
      setLoading(false);
    }
  };

  // Password strength indicator
  const getPasswordStrength = () => {
    if (!password) return { level: 0, text: "", color: colors.textSecondary };

    let strength = 0;
    if (password.length >= 8) strength++;
    if (/[A-Z]/.test(password)) strength++;
    if (/[0-9]/.test(password)) strength++;
    if (/[^A-Za-z0-9]/.test(password)) strength++;

    const levels = [
      { level: 1, text: "Weak", color: colors.error },
      { level: 2, text: "Fair", color: colors.warning },
      { level: 3, text: "Good", color: colors.primary },
      { level: 4, text: "Strong", color: colors.success },
    ];

    return levels[strength - 1] || levels[0];
  };

  const passwordStrength = getPasswordStrength();

  // Get availability indicator
  const getAvailabilityIcon = (
    available: boolean | null,
    checking: boolean,
  ) => {
    if (checking) return "⏳";
    if (available === true) return "✅";
    if (available === false) return "❌";
    return undefined;
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
            <Text style={styles.logo}>✨</Text>
            <Text style={[styles.title, { color: colors.text }]}>
              Join LAYERS
            </Text>
            <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
              Start exploring your city's hidden stories
            </Text>
          </View>

          {/* Form */}
          <View style={styles.form}>
            <Input
              label="Username"
              placeholder="coolexplorer"
              value={username}
              onChangeText={handleUsernameChange}
              error={errors.username}
              autoCapitalize="none"
              autoComplete="username"
              leftIcon="👤"
              rightIcon={getAvailabilityIcon(
                usernameAvailable,
                checkingUsername,
              )}
              hint="Letters, numbers, and underscores only"
              editable={!loading}
            />

            <Input
              label="Email"
              placeholder="your@email.com"
              value={email}
              onChangeText={handleEmailChange}
              error={errors.email}
              keyboardType="email-address"
              autoCapitalize="none"
              autoComplete="email"
              leftIcon="📧"
              rightIcon={getAvailabilityIcon(emailAvailable, checkingEmail)}
              editable={!loading}
            />

            <Input
              label="Password"
              placeholder="••••••••"
              value={password}
              onChangeText={(text) => {
                setPassword(text);
                clearError("password");
              }}
              error={errors.password}
              secureTextEntry={!showPassword}
              leftIcon="🔒"
              rightIcon={showPassword ? "👁️" : "👁️‍🗨️"}
              onRightIconPress={() => setShowPassword(!showPassword)}
              editable={!loading}
            />

            {/* Password Strength */}
            {password.length > 0 && (
              <View style={styles.strengthContainer}>
                <View style={styles.strengthBars}>
                  {[1, 2, 3, 4].map((level) => (
                    <View
                      key={level}
                      style={[
                        styles.strengthBar,
                        {
                          backgroundColor:
                            level <= passwordStrength.level
                              ? passwordStrength.color
                              : colors.border,
                        },
                      ]}
                    />
                  ))}
                </View>
                <Text
                  style={[
                    styles.strengthText,
                    { color: passwordStrength.color },
                  ]}
                >
                  {passwordStrength.text}
                </Text>
              </View>
            )}

            <Input
              label="Confirm Password"
              placeholder="••••••••"
              value={confirmPassword}
              onChangeText={(text) => {
                setConfirmPassword(text);
                clearError("confirmPassword");
              }}
              error={errors.confirmPassword}
              secureTextEntry={!showPassword}
              leftIcon="🔐"
              rightIcon={
                confirmPassword && password === confirmPassword
                  ? "✅"
                  : undefined
              }
              editable={!loading}
            />

            {/* Register Button */}
            <Button
              title="Create Account"
              onPress={handleRegister}
              loading={loading}
              icon="🚀"
              style={styles.registerButton}
            />

            {/* Terms */}
            <Text style={[styles.terms, { color: colors.textSecondary }]}>
              By creating an account, you agree to our{" "}
              <Text style={{ color: colors.primary }}>Terms of Service</Text>{" "}
              and <Text style={{ color: colors.primary }}>Privacy Policy</Text>
            </Text>
          </View>

          {/* Footer */}
          <View style={styles.footer}>
            <Text style={[styles.footerText, { color: colors.textSecondary }]}>
              Already have an account?{" "}
            </Text>
            <TouchableOpacity
              onPress={() => navigation.navigate("Login")}
              disabled={loading}
            >
              <Text style={[styles.linkText, { color: colors.primary }]}>
                Sign In
              </Text>
            </TouchableOpacity>
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
    marginTop: 32,
    marginBottom: 32,
  },
  logo: {
    fontSize: 56,
    marginBottom: 12,
  },
  title: {
    fontSize: 28,
    fontWeight: "bold",
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 15,
    textAlign: "center",
  },
  form: {
    marginBottom: 24,
  },
  strengthContainer: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: -12,
    marginBottom: 16,
  },
  strengthBars: {
    flexDirection: "row",
    flex: 1,
    gap: 4,
  },
  strengthBar: {
    flex: 1,
    height: 4,
    borderRadius: 2,
  },
  strengthText: {
    marginLeft: 12,
    fontSize: 12,
    fontWeight: "500",
  },
  registerButton: {
    marginTop: 8,
  },
  terms: {
    fontSize: 12,
    textAlign: "center",
    marginTop: 16,
    lineHeight: 18,
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
});
