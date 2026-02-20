// ===========================================
// LAYERS Main Navigator
// Bottom tabs: Map, Explore, Profile
// ===========================================

import React from "react";
import { View, Text, StyleSheet } from "react-native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { MainTabParamList } from "../types";
import { useAuthStore } from "../store/authStore";
import { Colors } from "../constants/colors";

import MapScreen from "../screens/main/MapScreen";
import ExploreScreen from "../screens/main/ExploreScreen";
import ProfileScreen from "../screens/main/ProfileScreen";

// Tab Icon Component
interface TabIconProps {
  name: string;
  focused: boolean;
  layer: "LIGHT" | "SHADOW";
}

const TabIcon = ({ name, focused, layer }: TabIconProps) => {
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];

  const icons: Record<string, string> = {
    Map: "🗺️",
    Explore: "🔍",
    Profile: "👤",
  };

  return (
    <View style={styles.tabIcon}>
      <Text style={[styles.tabEmoji, { opacity: focused ? 1 : 0.5 }]}>
        {icons[name]}
      </Text>
      <Text
        style={[
          styles.tabLabel,
          { color: focused ? colors.primary : colors.textSecondary },
        ]}
      >
        {name}
      </Text>
    </View>
  );
};

const Tab = createBottomTabNavigator<MainTabParamList>();

export default function MainNavigator() {
  const layer = useAuthStore((state) => state.layer);
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];

  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarStyle: {
          backgroundColor: colors.surface,
          borderTopColor: colors.border,
          borderTopWidth: 1,
          height: 85,
          paddingBottom: 25,
          paddingTop: 10,
        },
        tabBarShowLabel: false,
        tabBarIcon: ({ focused }) => (
          <TabIcon name={route.name} focused={focused} layer={layer} />
        ),
      })}
    >
      <Tab.Screen name="Map" component={MapScreen} />
      <Tab.Screen name="Explore" component={ExploreScreen} />
      <Tab.Screen name="Profile" component={ProfileScreen} />
    </Tab.Navigator>
  );
}

const styles = StyleSheet.create({
  tabIcon: {
    alignItems: "center",
    justifyContent: "center",
  },
  tabEmoji: {
    fontSize: 24,
  },
  tabLabel: {
    fontSize: 11,
    marginTop: 4,
    fontWeight: "500",
  },
});
