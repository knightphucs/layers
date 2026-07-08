// ===========================================
// LAYERS Onboarding Navigator (Week 9 Day 1)
// Story-mode flow shown ONCE per device after first login:
//   StoryIntro → LayerChoice → Permissions → FirstMission
// ===========================================

import React from 'react';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { OnboardingStackParamList } from '../types/onboarding';

import StoryIntroScreen from '../screens/onboarding/StoryIntroScreen';
import LayerChoiceScreen from '../screens/onboarding/LayerChoiceScreen';
import PermissionsScreen from '../screens/onboarding/PermissionsScreen';
import FirstMissionScreen from '../screens/onboarding/FirstMissionScreen';

const Stack = createNativeStackNavigator<OnboardingStackParamList>();

export default function OnboardingNavigator() {
    return (
        <Stack.Navigator
            screenOptions={{
                headerShown: false,
                contentStyle: { backgroundColor: '#101423' },
                animation: "fade", // story-mode feels cinematic, not app-like
                gestureEnabled: false, // no swipe-back - the flow is linear
            }}
        >
            <Stack.Screen name="StoryIntro" component={StoryIntroScreen} />
            <Stack.Screen name="LayerChoice" component={LayerChoiceScreen} />
            <Stack.Screen name="Permissions" component={PermissionsScreen} />
            <Stack.Screen name="FirstMission" component={FirstMissionScreen} />
        </Stack.Navigator>
    )
}