/**
 * Fresh & Warm Modern Grocery color palette for SmartBasket & KitchenSync.
 *
 * Dark Mode is the primary visual experience: deep warm charcoal-forest
 * surfaces, elevated warm slate cards, crisp off-white typography, emerald
 * primary CTA, amber (low) and coral/red (finished) pantry status tokens.
 *
 * Light Mode pairs warm cream/stone canvases with soft white cards and a
 * deep forest green primary CTA.
 */

export type ThemePalette = {
  // Core surfaces
  background: string;
  surface: string;
  surfaceElevated: string;
  surfaceMuted: string;

  // Borders
  border: string;
  borderSubtle: string;

  // Typography
  text: string;
  textSecondary: string;
  textMuted: string;

  // Brand & interactive CTAs
  tint: string;
  primary: string;
  primaryPressed: string;
  primaryMuted: string;
  primaryText: string;

  // Pantry & basket semantic statuses
  statusOk: string;
  statusOkBg: string;
  statusLow: string;
  statusLowBg: string;
  statusFinished: string;
  statusFinishedBg: string;
  accentSavings: string;
  accentSavingsBg: string;

  // Navigation & icons
  icon: string;
  tabIconDefault: string;
  tabIconSelected: string;
  tabBarBg: string;
  tabBarBorder: string;
};

export const Colors: { light: ThemePalette; dark: ThemePalette } = {
  dark: {
    background: '#111613',
    surface: '#1A221D',
    surfaceElevated: '#232D27',
    surfaceMuted: '#161C18',

    border: '#2D3A32',
    borderSubtle: '#222C26',

    text: '#F5F4EE',
    textSecondary: '#B6C2B9',
    textMuted: '#839187',

    tint: '#24C77E',
    primary: '#24C77E',
    primaryPressed: '#1DA96A',
    primaryMuted: '#153B2B',
    primaryText: '#0A1912',

    statusOk: '#24C77E',
    statusOkBg: '#143527',
    statusLow: '#F5A524',
    statusLowBg: '#3A2B11',
    statusFinished: '#F87171',
    statusFinishedBg: '#3F1D20',
    accentSavings: '#34D399',
    accentSavingsBg: '#133A2A',

    icon: '#9AA89E',
    tabIconDefault: '#839187',
    tabIconSelected: '#24C77E',
    tabBarBg: '#151B17',
    tabBarBorder: '#243029',
  },
  light: {
    background: '#F7F4EE',
    surface: '#FFFFFF',
    surfaceElevated: '#F1ECE3',
    surfaceMuted: '#EFEAE0',

    border: '#E2DBD0',
    borderSubtle: '#EDE7DC',

    text: '#1A241E',
    textSecondary: '#4B5B51',
    textMuted: '#738278',

    tint: '#166534',
    primary: '#166534',
    primaryPressed: '#14532D',
    primaryMuted: '#DCFCE7',
    primaryText: '#FFFFFF',

    statusOk: '#15803D',
    statusOkBg: '#DCFCE7',
    statusLow: '#B45309',
    statusLowBg: '#FEF3C7',
    statusFinished: '#DC2626',
    statusFinishedBg: '#FEE2E2',
    accentSavings: '#15803D',
    accentSavingsBg: '#DCFCE7',

    icon: '#5A6A60',
    tabIconDefault: '#738278',
    tabIconSelected: '#166534',
    tabBarBg: '#FCFBF7',
    tabBarBorder: '#E5DFD5',
  },
};
