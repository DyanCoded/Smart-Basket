/**
 * Subtle top application chrome bar displaying the SmartBasket brand badge,
 * live Sync Status Pill (Synced vs. Syncing vs. Offline), and a quick
 * Dark / Light theme toggle button.
 */

import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { IconSymbol } from '@/components/ui/IconSymbol';
import { Radii, Spacing } from '@/constants/Theme';
import { useSyncStatus } from '@/context/SyncStatusContext';
import { useAppTheme } from '@/context/ThemeContext';

export function SyncStatusBar() {
  const insets = useSafeAreaInsets();
  const { colors, isDark, toggleTheme } = useAppTheme();
  const { status, pendingCount, probeBackendHealth } = useSyncStatus();

  const statusConfig =
    status === 'synced'
      ? {
          label: 'Synced',
          dotColor: colors.statusOk,
          bgColor: colors.statusOkBg,
          textColor: colors.statusOk,
        }
      : status === 'syncing'
        ? {
            label: pendingCount > 0 ? `Syncing (${pendingCount})` : 'Syncing…',
            dotColor: colors.statusLow,
            bgColor: colors.statusLowBg,
            textColor: colors.statusLow,
          }
        : {
            label: pendingCount > 0 ? `Offline (${pendingCount})` : 'Offline',
            dotColor: colors.statusFinished,
            bgColor: colors.statusFinishedBg,
            textColor: colors.statusFinished,
          };

  return (
    <View
      style={[
        styles.wrapper,
        {
          paddingTop: Math.max(insets.top, Spacing.sm) + 4,
          backgroundColor: colors.tabBarBg,
          borderBottomColor: colors.tabBarBorder,
        },
      ]}>
      <View style={styles.brandGroup}>
        <View style={[styles.brandDot, { backgroundColor: colors.primary }]} />
        <Text style={[styles.brandTitle, { color: colors.text }]}>
          SmartBasket
        </Text>
      </View>

      <View style={styles.rightControls}>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={`Sync status: ${statusConfig.label}. Tap to check connection.`}
          onPress={() => void probeBackendHealth()}
          style={({ pressed }) => [
            styles.syncPill,
            {
              backgroundColor: statusConfig.bgColor,
              borderColor: colors.borderSubtle,
              opacity: pressed ? 0.78 : 1,
            },
          ]}>
          <View
            style={[
              styles.statusDot,
              { backgroundColor: statusConfig.dotColor },
            ]}
          />
          <Text style={[styles.syncLabel, { color: statusConfig.textColor }]}>
            {statusConfig.label}
          </Text>
        </Pressable>

        <Pressable
          accessibilityRole="button"
          accessibilityLabel={`Switch to ${isDark ? 'Light' : 'Dark'} Mode`}
          onPress={toggleTheme}
          style={({ pressed }) => [
            styles.themeButton,
            {
              backgroundColor: colors.surfaceElevated,
              borderColor: colors.border,
              opacity: pressed ? 0.78 : 1,
            },
          ]}>
          <IconSymbol
            name={isDark ? 'sun.max.fill' : 'moon.fill'}
            size={16}
            color={colors.text}
          />
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: Spacing.lg,
    paddingBottom: Spacing.sm + 2,
    borderBottomWidth: 1,
  },
  brandGroup: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
  },
  brandDot: {
    width: 10,
    height: 10,
    borderRadius: Radii.pill,
  },
  brandTitle: {
    fontSize: 16,
    fontWeight: '800',
    letterSpacing: -0.2,
  },
  rightControls: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
  },
  syncPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: Radii.pill,
    borderWidth: 1,
  },
  statusDot: {
    width: 7,
    height: 7,
    borderRadius: Radii.pill,
  },
  syncLabel: {
    fontSize: 12,
    fontWeight: '700',
  },
  themeButton: {
    width: 32,
    height: 32,
    borderRadius: Radii.pill,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
