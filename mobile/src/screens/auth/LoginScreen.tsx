// ===========================================
// src/screens/auth/LoginScreen.tsx
// ===========================================

import React, { useState, useEffect, useRef } from "react";
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
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { Ionicons, AntDesign } from "@expo/vector-icons";

import { AuthStackParamList } from "../../types";
import { useAuthStore } from "../../store/authStore";
import { authService, getErrorMessage, isNetworkError } from "../../services";
import { Input, Button, Divider } from "../../components";
import { Colors } from "../../constants/colors";

type Props = {
  navigation: NativeStackNavigationProp<AuthStackParamList, "Login">;
};

export default function LoginScreen({ navigation }: Props) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<{ email?: string; password?: string }>(
    {},
  );

  const { login, layer } = useAuthStore();
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];

  // -----------------------------------------------------------------
  // 🚀 Animation setup: Snappy "Pop & Rest" Logo
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

  // Tie the physical layers to the 0 -> 1 master progress
  const Y1 = progress.interpolate({ inputRange: [0, 1], outputRange: [8, 16] });
  const Y2 = progress.interpolate({ inputRange: [0, 1], outputRange: [0, 0] });
  const Y3 = progress.interpolate({
    inputRange: [0, 1],
    outputRange: [-8, -16],
  }); // Top pushes up

  // Validation & Login Logic
  const validate = (): boolean => {
    const newErrors: { email?: string; password?: string } = {};
    if (!email.trim()) newErrors.email = "Email is required";
    else if (!/\S+@\S+\.\S+/.test(email))
      newErrors.email = "Please enter a valid email";

    if (!password) newErrors.password = "Password is required";
    else if (password.length < 8)
      newErrors.password = "Password must be at least 8 characters";

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleLogin = async () => {
    if (!validate()) return;
    setLoading(true);
    try {
      const response = await authService.login({
        email: email.trim().toLowerCase(),
        password,
      });
      await login(response.user, {
        access_token: response.access_token,
        refresh_token: response.refresh_token,
        token_type: response.token_type,
      });
    } catch (error: any) {
      if (isNetworkError(error)) {
        Alert.alert(
          "Connection Error",
          "Unable to connect to server. Check your connection.",
          [{ text: "OK" }],
        );
      } else {
        Alert.alert("Login Failed", getErrorMessage(error));
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

            <Text style={[styles.title, { color: colors.text }]}>LAYERS</Text>
            <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
              See the hidden layers of your city
            </Text>
          </View>

          {/* Form */}
          <View style={styles.form}>
            <View style={styles.inputGroup}>
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
                leftIcon={
                  <Ionicons
                    name="mail-outline"
                    size={20}
                    color={colors.textSecondary}
                  />
                }
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
            </View>

            <TouchableOpacity
              onPress={() => navigation.navigate("ForgotPassword")}
              style={styles.forgotLink}
              disabled={loading}
            >
              <Text
                style={[styles.forgotText, { color: colors.textSecondary }]}
              >
                Forgot password?
              </Text>
            </TouchableOpacity>

            <View style={styles.buttonContainer}>
              <Button title="Sign In" onPress={handleLogin} loading={loading} />
            </View>

            <Divider text="or continue with" />

            <View style={styles.socialRow}>
              <Button
                title="Google"
                onPress={() => Alert.alert("Coming Soon")}
                variant="outline"
                icon={<AntDesign name="google" size={20} color={colors.text} />}
                style={[styles.socialButton, { borderColor: colors.border }]}
                textStyle={{ color: colors.text }}
                disabled={loading}
              />
              <Button
                title="Apple"
                onPress={() => Alert.alert("Coming Soon")}
                variant="outline"
                icon={<AntDesign name="apple" size={20} color={colors.text} />}
                style={[styles.socialButton, { borderColor: colors.border }]}
                textStyle={{ color: colors.text }}
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
              style={styles.signupTouchable}
            >
              <Text style={[styles.linkText, { color: colors.primary }]}>
                Sign Up
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
    paddingHorizontal: 28,
    paddingBottom: 40,
    justifyContent: "center",
  },
  header: { alignItems: "center", marginTop: 20, marginBottom: 48 },
  logoContainer: {
    width: 96,
    height: 96,
    borderRadius: 28,
    justifyContent: "center",
    alignItems: "center",
    marginBottom: 24,
    position: "relative",
  },

  // Adjusted customLayer to perfectly mimic the real icon
  customLayer: {
    position: "absolute",
    width: 44,
    height: 44,
    borderRadius: 6,
    borderWidth: 2.5,
  },

  title: { fontSize: 32, fontWeight: "800", letterSpacing: 2, marginBottom: 8 },
  subtitle: { fontSize: 16, textAlign: "center", opacity: 0.8 },
  form: { marginBottom: 16 },
  inputGroup: { gap: 0 },
  forgotLink: {
    alignSelf: "flex-end",
    marginTop: -8,
    marginBottom: 20,
    paddingVertical: 8,
    paddingLeft: 16,
  },
  forgotText: { fontSize: 14, fontWeight: "600" },
  buttonContainer: {
    marginBottom: 24,
    shadowColor: "#000",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 12,
    elevation: 4,
  },
  socialRow: { flexDirection: "row", gap: 16, marginTop: 8 },
  socialButton: { flex: 1 },
  footer: {
    flexDirection: "row",
    justifyContent: "center",
    alignItems: "center",
    marginTop: 16,
  },
  footerText: { fontSize: 15 },
  signupTouchable: { paddingVertical: 8, paddingHorizontal: 4 },
  linkText: { fontSize: 15, fontWeight: "700" },
});
