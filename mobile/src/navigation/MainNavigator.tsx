// ===========================================
// LAYERS — Main Navigator
// Tabs: Map | Inbox | Explore | Profile
// ===========================================

import React from "react";
import { View, Text, StyleSheet } from "react-native";
import { createBottomTabNavigator } from "@react-navigation/bottom-tabs";
import { MainTabParamList } from "../types";
import { useAuthStore } from "../store/authStore";
import { useInboxStore } from "../store/inboxStore";
import { Colors } from "../constants/colors";

import MapScreen from "../screens/main/MapScreen";
import InboxScreen from "../screens/main/InboxScreen";
import ExploreScreen from "../screens/main/ExploreScreen";
import ProfileScreen from "../screens/main/ProfileScreen";

// ============================================================
// TAB ICON COMPONENT
// ============================================================

interface TabIconProps {
  name: string;
  focused: boolean;
  layer: "LIGHT" | "SHADOW";
  badge?: number;
}

const TabIcon = ({ name, focused, layer, badge }: TabIconProps) => {
  const colors = Colors[layer.toLowerCase() as "light" | "shadow"];

  const icons: Record<string, string> = {
    Map: "🗺️",
    Inbox: "💌",
    Explore: "🔍",
    Profile: "👤",
  };

  return (
    <View style={styles.tabIcon}>
      <View>
        <Text style={[styles.tabEmoji, { opacity: focused ? 1 : 0.5 }]}>
          {icons[name]}
        </Text>
        {/* Unread badge */}
        {badge !== undefined && badge > 0 && (
          <View style={[styles.tabBadge, { backgroundColor: colors.primary }]}>
            <Text style={styles.tabBadgeText}>{badge > 9 ? "9+" : badge}</Text>
          </View>
        )}
      </View>
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

// ============================================================
// NAVIGATOR
// ============================================================

const Tab = createBottomTabNavigator<MainTabParamList>();

export default function MainNavigator() {
  const layer = useAuthStore((state) => state.layer);
  const unreadCount = useInboxStore((state) => state.unreadCount);
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
          <TabIcon
            name={route.name}
            focused={focused}
            layer={layer}
            badge={route.name === "Inbox" ? unreadCount : undefined}
          />
        ),
      })}
    >
      <Tab.Screen name="Map" component={MapScreen} />
      <Tab.Screen name="Inbox" component={InboxScreen} />
      <Tab.Screen name="Explore" component={ExploreScreen} />
      <Tab.Screen name="Profile" component={ProfileScreen} />
    </Tab.Navigator>
  );
}

// ============================================================
// STYLES
// ============================================================

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
  tabBadge: {
    position: "absolute",
    top: -4,
    right: -10,
    minWidth: 18,
    height: 18,
    borderRadius: 9,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 4,
  },
  tabBadgeText: {
    color: "#FFFFFF",
    fontSize: 10,
    fontWeight: "700",
  },
});
