import { Tabs } from 'expo-router';
import React from 'react';
import { Platform, StyleSheet, View } from 'react-native';

import { HapticTab } from '@/components/HapticTab';
import { SyncStatusBar } from '@/components/SyncStatusBar';
import { IconSymbol } from '@/components/ui/IconSymbol';
import { useAppTheme } from '@/context/ThemeContext';

export default function TabLayout() {
  const { colors } = useAppTheme();

  return (
    <View style={[styles.root, { backgroundColor: colors.background }]}>
      <SyncStatusBar />
      <Tabs
        screenOptions={{
          headerShown: false,
          tabBarActiveTintColor: colors.tabIconSelected,
          tabBarInactiveTintColor: colors.tabIconDefault,
          tabBarButton: (props) => (
            <HapticTab
              {...props}
              pressColor={
                props.pressColor ? String(props.pressColor) : undefined
              }
              hoverEffect={undefined}
            />
          ),
          tabBarLabelStyle: {
            fontSize: 12,
            fontWeight: '700',
            marginBottom: Platform.OS === 'ios' ? 0 : 4,
          },
          tabBarStyle: {
            backgroundColor: colors.tabBarBg,
            borderTopColor: colors.tabBarBorder,
            borderTopWidth: 1,
            height: Platform.OS === 'ios' ? 84 : 64,
            paddingTop: 6,
          },
        }}>
        <Tabs.Screen
          name="index"
          options={{
            title: 'Pantry',
            tabBarIcon: ({ color }) => (
              <IconSymbol
                size={24}
                name="tray.full.fill"
                color={String(color)}
              />
            ),
          }}
        />
        <Tabs.Screen
          name="explore"
          options={{
            title: 'Basket',
            tabBarIcon: ({ color }) => (
              <IconSymbol size={24} name="basket.fill" color={String(color)} />
            ),
          }}
        />
        <Tabs.Screen
          name="home"
          options={{
            title: 'Home',
            tabBarIcon: ({ color }) => (
              <IconSymbol size={24} name="house.fill" color={String(color)} />
            ),
          }}
        />
      </Tabs>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
  },
});
