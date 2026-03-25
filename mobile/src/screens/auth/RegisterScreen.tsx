import React, { useState, useCallback, useRef, useEffect } from "react";
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  Alert,
  Animated,
  Easing,
  ActivityIndicator,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { Ionicons } from "@expo/vector-icons";

import { AuthStackParamList } from "../../types";
import { useAuthStore } from "../../store/authStore";
import { authService, getErrorMessage, isNetworkError } from "../../services";
import { Input, Button } from "../../components";
import { Colors } from "../../constants/colors";

type Props = {
  navigation: NativeStackNavigationProp<AuthStackParamList, "Register">;
};

// Debounce helper
const useDebounce = () => {
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | undefined>(
    undefined,
  );

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

  // -----------------------------------------------------------------
  // 🚀 Animation setup: Snappy "Pop & Rest" Logo (Matching Login)
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

  // -----------------------------------------------------------------
  // Logic
  // -----------------------------------------------------------------
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

  const handleUsernameChange = (text: string) => {
    const cleaned = text.toLowerCase().replace(/[^a-z0-9_]/g, "");
    setUsername(cleaned);
    setUsernameAvailable(null);
    clearError("username");
    if (cleaned.length >= 3) {
      debounce(() => checkUsernameAvailability(cleaned), 500);
    }
  };

  const handleEmailChange = (text: string) => {
    setEmail(text);
    setEmailAvailable(null);
    clearError("email");
    if (/\S+@\S+\.\S+/.test(text)) {
      debounce(() => checkEmailAvailability(text), 500);
    }
  };

  const validate = (): boolean => {
    const newErrors: typeof errors = {};

    if (!username.trim()) newErrors.username = "Username is required";
    else if (username.length < 3)
      newErrors.username = "Username must be at least 3 characters";
    else if (!/^[a-zA-Z0-9_]+$/.test(username))
      newErrors.username = "Letters, numbers, and underscores only";
    else if (usernameAvailable === false)
      newErrors.username = "Username is already taken";

    if (!email.trim()) newErrors.email = "Email is required";
    else if (!/\S+@\S+\.\S+/.test(email))
      newErrors.email = "Please enter a valid email";
    else if (emailAvailable === false)
      newErrors.email = "Email is already registered";

    if (!password) newErrors.password = "Password is required";
    else if (password.length < 8)
      newErrors.password = "Password must be at least 8 characters";
    else if (!/(?=.*[0-9])/.test(password))
      newErrors.password = "Password must contain at least one number";

    if (!confirmPassword)
      newErrors.confirmPassword = "Please confirm your password";
    else if (password !== confirmPassword)
      newErrors.confirmPassword = "Passwords do not match";

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const clearError = (field: keyof typeof errors) => {
    if (errors[field]) setErrors({ ...errors, [field]: undefined });
  };

  const handleRegister = async () => {
    if (!validate()) return;
    setLoading(true);

    try {
      const response = await authService.register({
        email: email.trim().toLowerCase(),
        username: username.trim().toLowerCase(),
        password,
      });

      await login(response.user, {
        access_token: response.access_token,
        refresh_token: response.refresh_token,
        token_type: response.token_type,
      });

      Alert.alert(
        "Welcome to LAYERS! 🌆",
        `Your account has been created successfully, ${response.user.username}!`,
        [{ text: "Start Exploring!" }],
      );
    } catch (error: any) {
      if (isNetworkError(error)) {
        Alert.alert(
          "Connection Error",
          "Unable to connect to server. Please check your connection and try again.",
          [{ text: "OK" }],
        );
      } else {
        Alert.alert("Registration Failed", getErrorMessage(error));
      }
    } finally {
      setLoading(false);
    }
  };

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

  // Clean UI helper for icons
  const renderAvailabilityIcon = (
    available: boolean | null,
    checking: boolean,
  ) => {
    if (checking)
      return <ActivityIndicator size="small" color={colors.primary} />;
    if (available === true)
      return (
        <Ionicons name="checkmark-circle" size={20} color={colors.success} />
      );
    if (available === false)
      return <Ionicons name="close-circle" size={20} color={colors.error} />;
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
            <View
              style={[
                styles.logoContainer,
                { backgroundColor: colors.primary + "15" },
              ]}
            >
              {/* BOTTOM LAYER */}
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
              {/* MIDDLE LAYER */}
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
              {/* TOP LAYER */}
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

            <Text style={[styles.title, { color: colors.text }]}>
              JOIN LAYERS
            </Text>
            <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
              Start exploring your city's hidden stories
            </Text>
          </View>

          {/* Form */}
          <View style={styles.form}>
            <View style={styles.inputGroup}>
              <Input
                label="Username"
                placeholder="coolexplorer"
                value={username}
                onChangeText={handleUsernameChange}
                error={errors.username}
                autoCapitalize="none"
                autoComplete="username"
                leftIcon={
                  <Ionicons
                    name="person-outline"
                    size={20}
                    color={colors.textSecondary}
                  />
                }
                rightIcon={renderAvailabilityIcon(
                  usernameAvailable,
                  checkingUsername,
                )}
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
                leftIcon={
                  <Ionicons
                    name="mail-outline"
                    size={20}
                    color={colors.textSecondary}
                  />
                }
                rightIcon={renderAvailabilityIcon(
                  emailAvailable,
                  checkingEmail,
                )}
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
                leftIcon={
                  <Ionicons
                    name="lock-closed-outline"
                    size={20}
                    color={colors.textSecondary}
                  />
                }
                rightIcon={
                  <Ionicons
                    name={showPassword ? "eye-off-outline" : "eye-outline"}
                    size={20}
                    color={colors.textSecondary}
                  />
                }
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
                leftIcon={
                  <Ionicons
                    name="shield-checkmark-outline"
                    size={20}
                    color={colors.textSecondary}
                  />
                }
                rightIcon={
                  confirmPassword && password === confirmPassword ? (
                    <Ionicons
                      name="checkmark-circle"
                      size={20}
                      color={colors.success}
                    />
                  ) : undefined
                }
                editable={!loading}
              />
            </View>

            <View style={styles.buttonContainer}>
              <Button
                title="Create Account"
                onPress={handleRegister}
                loading={loading}
              />
            </View>

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
              style={styles.signinTouchable}
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
  container: { flex: 1 },
  keyboard: { flex: 1 },
  scroll: {
    flexGrow: 1,
    paddingHorizontal: 28, // Matched Login
    paddingBottom: 40,
    justifyContent: "center",
  },
  header: { alignItems: "center", marginTop: 20, marginBottom: 40 },
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
  form: { marginBottom: 16 },
  inputGroup: { gap: 0 }, // Matched Login
  strengthContainer: {
    flexDirection: "row",
    alignItems: "center",
    marginTop: -8,
    marginBottom: 16,
    paddingHorizontal: 4,
  },
  strengthBars: { flexDirection: "row", flex: 1, gap: 6 },
  strengthBar: { flex: 1, height: 4, borderRadius: 2 },
  strengthText: { marginLeft: 12, fontSize: 12, fontWeight: "600" },
  buttonContainer: {
    marginTop: 16,
    marginBottom: 8,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 12,
    elevation: 4, // Matched Login
  },
  terms: { fontSize: 12, textAlign: "center", marginTop: 16, lineHeight: 18 },
  footer: {
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    marginTop: 16, // Matched Login
  },
  footerText: { fontSize: 15 },
  signinTouchable: { paddingVertical: 8, paddingHorizontal: 4 },
  linkText: { fontSize: 15, fontWeight: "700" },
});
