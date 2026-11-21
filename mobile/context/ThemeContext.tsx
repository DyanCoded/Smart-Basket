/**
 * Persistent Warm Grocery theme provider (Dark Mode primary + Light Mode + System).
 * Persists user preference via SQLite (native) and localStorage (web).
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';
import { useColorScheme as useSystemColorScheme } from 'react-native';

import { Colors, type ThemePalette } from '@/constants/Colors';
import {
  type ResolvedColorScheme,
  type ThemePreference,
} from '@/constants/Theme';
import { getUserPreference, setUserPreference } from '@/db/sqlite';

const THEME_PREF_KEY = 'theme_preference';

export interface AppThemeContextValue {
  preference: ThemePreference;
  colorScheme: ResolvedColorScheme;
  colors: ThemePalette;
  isDark: boolean;
  isLoaded: boolean;
  setPreference: (next: ThemePreference) => void;
  toggleTheme: () => void;
}

const ThemeContext = createContext<AppThemeContextValue | null>(null);

function isValidThemePreference(value: string | null): value is ThemePreference {
  return value === 'dark' || value === 'light' || value === 'system';
}

export function AppThemeProvider({ children }: { children: React.ReactNode }) {
  const systemScheme = useSystemColorScheme();
  // Dark Mode is the primary visual experience for SmartBasket (#25)
  const [preference, setPreferenceState] = useState<ThemePreference>('dark');
  const [isLoaded, setIsLoaded] = useState<boolean>(false);

  useEffect(() => {
    let mounted = true;
    void (async () => {
      try {
        const stored = await getUserPreference(THEME_PREF_KEY);
        if (mounted && isValidThemePreference(stored)) {
          setPreferenceState(stored);
        }
      } finally {
        if (mounted) {
          setIsLoaded(true);
        }
      }
    })();

    return () => {
      mounted = false;
    };
  }, []);

  const colorScheme: ResolvedColorScheme = useMemo(() => {
    if (preference === 'system') {
      return systemScheme === 'light' ? 'light' : 'dark';
    }
    return preference;
  }, [preference, systemScheme]);

  const setPreference = useCallback((next: ThemePreference) => {
    setPreferenceState(next);
    void setUserPreference(THEME_PREF_KEY, next);
  }, []);

  const toggleTheme = useCallback(() => {
    const next: ThemePreference = colorScheme === 'dark' ? 'light' : 'dark';
    setPreference(next);
  }, [colorScheme, setPreference]);

  const value = useMemo<AppThemeContextValue>(
    () => ({
      preference,
      colorScheme,
      colors: Colors[colorScheme],
      isDark: colorScheme === 'dark',
      isLoaded,
      setPreference,
      toggleTheme,
    }),
    [preference, colorScheme, isLoaded, setPreference, toggleTheme]
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useOptionalAppTheme(): AppThemeContextValue | null {
  return useContext(ThemeContext);
}

export function useAppTheme(): AppThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) {
    return {
      preference: 'dark',
      colorScheme: 'dark',
      colors: Colors.dark,
      isDark: true,
      isLoaded: true,
      setPreference: () => undefined,
      toggleTheme: () => undefined,
    };
  }
  return ctx;
}
