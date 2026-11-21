/**
 * Warm Grocery design tokens: spacing scale, radii, typography, soft shadows,
 * and React Navigation theme integration for Dark (primary) & Light modes.
 */

import { DarkTheme, DefaultTheme, type Theme } from '@react-navigation/native';
import { Platform, type TextStyle, type ViewStyle } from 'react-native';

import { Colors, type ThemePalette } from '@/constants/Colors';

export type ResolvedColorScheme = 'dark' | 'light';
export type ThemePreference = 'dark' | 'light' | 'system';

export const Spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  xxl: 28,
} as const;

export const Radii = {
  sm: 10,
  md: 14,
  lg: 18,
  xl: 24,
  pill: 999,
} as const;

export const Typography: Record<
  'hero' | 'title' | 'subtitle' | 'cardTitle' | 'body' | 'bodySemiBold' | 'caption' | 'badge',
  TextStyle
> = {
  hero: {
    fontSize: 30,
    lineHeight: 36,
    fontWeight: '800',
    letterSpacing: -0.5,
  },
  title: {
    fontSize: 24,
    lineHeight: 30,
    fontWeight: '700',
    letterSpacing: -0.3,
  },
  subtitle: {
    fontSize: 18,
    lineHeight: 24,
    fontWeight: '700',
  },
  cardTitle: {
    fontSize: 16,
    lineHeight: 22,
    fontWeight: '700',
  },
  body: {
    fontSize: 15,
    lineHeight: 22,
    fontWeight: '400',
  },
  bodySemiBold: {
    fontSize: 15,
    lineHeight: 22,
    fontWeight: '600',
  },
  caption: {
    fontSize: 13,
    lineHeight: 18,
    fontWeight: '500',
  },
  badge: {
    fontSize: 11,
    lineHeight: 14,
    fontWeight: '700',
    letterSpacing: 0.4,
    textTransform: 'uppercase',
  },
};

export function getCardShadow(scheme: ResolvedColorScheme): ViewStyle {
  if (Platform.OS === 'web') {
    return {
      boxShadow:
        scheme === 'dark'
          ? '0px 6px 18px rgba(0, 0, 0, 0.28)'
          : '0px 6px 16px rgba(26, 36, 30, 0.06)',
    } as ViewStyle;
  }

  return scheme === 'dark'
    ? {
        shadowColor: '#000000',
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.28,
        shadowRadius: 10,
        elevation: 4,
      }
    : {
        shadowColor: '#1A241E',
        shadowOffset: { width: 0, height: 3 },
        shadowOpacity: 0.08,
        shadowRadius: 8,
        elevation: 2,
      };
}

export function getNavigationTheme(scheme: ResolvedColorScheme): Theme {
  const base = scheme === 'dark' ? DarkTheme : DefaultTheme;
  const palette: ThemePalette = Colors[scheme];

  return {
    ...base,
    dark: scheme === 'dark',
    colors: {
      ...base.colors,
      primary: palette.primary,
      background: palette.background,
      card: palette.tabBarBg,
      text: palette.text,
      border: palette.borderSubtle,
      notification: palette.statusLow,
    },
  };
}
