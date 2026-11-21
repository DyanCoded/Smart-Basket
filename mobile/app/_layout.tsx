import { ThemeProvider } from '@react-navigation/native';
import { useFonts } from 'expo-font';
import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import React from 'react';
import 'react-native-reanimated';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { getNavigationTheme } from '@/constants/Theme';
import { SyncStatusProvider } from '@/context/SyncStatusContext';
import { AppThemeProvider, useAppTheme } from '@/context/ThemeContext';

if (typeof globalThis.setImmediate === 'undefined') {
  (
    globalThis as unknown as {
      setImmediate: (fn: () => void) => ReturnType<typeof setTimeout>;
    }
  ).setImmediate = (fn: () => void) => setTimeout(fn, 0);
}

function RootNavigatorShell() {
  const { colorScheme, isDark } = useAppTheme();

  return (
    <ThemeProvider value={getNavigationTheme(colorScheme)}>
      <Stack>
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        <Stack.Screen
          name="product/[id]"
          options={{
            presentation: 'modal',
            headerShown: false,
          }}
        />
        <Stack.Screen name="+not-found" />
      </Stack>
      <StatusBar style={isDark ? 'light' : 'dark'} />
    </ThemeProvider>
  );
}

export default function RootLayout() {
  const [loaded] = useFonts({
    SpaceMono: require('../assets/fonts/SpaceMono-Regular.ttf'),
  });

  if (!loaded) {
    // Async font loading only occurs in development.
    return null;
  }

  return (
    <SafeAreaProvider>
      <AppThemeProvider>
        <SyncStatusProvider>
          <RootNavigatorShell />
        </SyncStatusProvider>
      </AppThemeProvider>
    </SafeAreaProvider>
  );
}
