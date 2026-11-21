/**
 * Home Tab — Household Overview, Appearance Theme Switcher (Dark / Light / System),
 * and Live Catalog Freshness Telemetry.
 */

import { useRouter } from 'expo-router';
import React from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { IconSymbol } from '@/components/ui/IconSymbol';
import {
  getCardShadow,
  Radii,
  Spacing,
  type ThemePreference,
  Typography,
} from '@/constants/Theme';
import { useSyncStatus } from '@/context/SyncStatusContext';
import { useAppTheme } from '@/context/ThemeContext';
import { getActiveHomeId, getApiBaseUrl } from '@/services/api';

const THEME_OPTIONS: {
  value: ThemePreference;
  label: string;
  description: string;
}[] = [
  {
    value: 'dark',
    label: 'Dark',
    description: 'Deep charcoal-forest & emerald (Primary)',
  },
  {
    value: 'light',
    label: 'Light',
    description: 'Warm cream stone & forest green',
  },
  {
    value: 'system',
    label: 'System',
    description: 'Match device appearance automatically',
  },
];

function formatFreshnessTimestamp(iso: string | null): string {
  if (!iso) {
    return 'Not yet verified';
  }
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) {
    return iso;
  }
  return parsed.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function HomeTabScreen() {
  const router = useRouter();
  const { colors, colorScheme, preference, setPreference } = useAppTheme();
  const {
    status,
    pendingCount,
    lastSyncedAt,
    catalogLastSyncAt,
    trackedPricesCount,
    probeBackendHealth,
  } = useSyncStatus();

  const cardShadow = getCardShadow(colorScheme);
  const homeId = getActiveHomeId() ?? '00000000-0000-4000-8000-000000000001';

  return (
    <ScrollView
      style={{ backgroundColor: colors.background }}
      contentContainerStyle={styles.container}>
      {/* Hero Banner */}
      <View
        style={[
          styles.heroCard,
          cardShadow,
          {
            backgroundColor: colors.surface,
            borderColor: colors.border,
          },
        ]}>
        <View
          style={[
            styles.eyebrowBadge,
            { backgroundColor: colors.primaryMuted },
          ]}>
          <Text style={[styles.eyebrowText, { color: colors.primary }]}>
            KITCHENSYNC HOUSEHOLD
          </Text>
        </View>
        <Text style={[Typography.title, { color: colors.text }]}>
          Home & Preferences
        </Text>
        <Text style={[Typography.body, { color: colors.textSecondary }]}>
          Manage your household sync connection, catalog price freshness, and
          Warm Grocery appearance theme.
        </Text>
      </View>

      {/* Appearance / Dark & Light Theme Persistence */}
      <View
        style={[
          styles.card,
          cardShadow,
          {
            backgroundColor: colors.surface,
            borderColor: colors.border,
          },
        ]}>
        <View style={styles.sectionHeader}>
          <Text style={[Typography.subtitle, { color: colors.text }]}>
            Appearance
          </Text>
          <Text style={[Typography.caption, { color: colors.textMuted }]}>
            Saved automatically
          </Text>
        </View>

        <View
          style={[
            styles.segmentedTrack,
            {
              backgroundColor: colors.surfaceMuted,
              borderColor: colors.borderSubtle,
            },
          ]}>
          {THEME_OPTIONS.map((option) => {
            const isSelected = preference === option.value;
            return (
              <Pressable
                key={option.value}
                accessibilityRole="button"
                accessibilityState={{ selected: isSelected }}
                onPress={() => setPreference(option.value)}
                style={[
                  styles.segmentPill,
                  isSelected && {
                    backgroundColor: colors.primary,
                  },
                ]}>
                <Text
                  style={[
                    styles.segmentLabel,
                    {
                      color: isSelected
                        ? colors.primaryText
                        : colors.textSecondary,
                    },
                  ]}>
                  {option.label}
                </Text>
              </Pressable>
            );
          })}
        </View>

        <Text style={[Typography.caption, { color: colors.textSecondary }]}>
          {
            THEME_OPTIONS.find((opt) => opt.value === preference)?.description
          }
        </Text>
      </View>

      {/* Live Sync & Catalog Freshness Card */}
      <View
        style={[
          styles.card,
          cardShadow,
          {
            backgroundColor: colors.surface,
            borderColor: colors.border,
          },
        ]}>
        <View style={styles.sectionHeader}>
          <Text style={[Typography.subtitle, { color: colors.text }]}>
            Sync & Price Freshness
          </Text>
          <View
            style={[
              styles.statusChip,
              {
                backgroundColor:
                  status === 'synced'
                    ? colors.statusOkBg
                    : status === 'syncing'
                      ? colors.statusLowBg
                      : colors.statusFinishedBg,
              },
            ]}>
            <Text
              style={[
                Typography.badge,
                {
                  color:
                    status === 'synced'
                      ? colors.statusOk
                      : status === 'syncing'
                        ? colors.statusLow
                        : colors.statusFinished,
                },
              ]}>
              {status === 'synced'
                ? 'Synced'
                : status === 'syncing'
                  ? 'Syncing'
                  : 'Offline'}
            </Text>
          </View>
        </View>

        <View
          style={[
            styles.metaList,
            {
              backgroundColor: colors.surfaceElevated,
              borderColor: colors.borderSubtle,
            },
          ]}>
          <View style={styles.metaRow}>
            <Text style={[Typography.caption, { color: colors.textMuted }]}>
              Active Household ID
            </Text>
            <Text
              numberOfLines={1}
              style={[styles.metaValue, { color: colors.text }]}>
              {homeId.slice(0, 8)}…{homeId.slice(-4)}
            </Text>
          </View>
          <View style={styles.metaRow}>
            <Text style={[Typography.caption, { color: colors.textMuted }]}>
              Pending Offline Edits
            </Text>
            <Text style={[styles.metaValue, { color: colors.text }]}>
              {pendingCount}
            </Text>
          </View>
          <View style={styles.metaRow}>
            <Text style={[Typography.caption, { color: colors.textMuted }]}>
              Last Pantry Sync
            </Text>
            <Text style={[styles.metaValue, { color: colors.text }]}>
              {formatFreshnessTimestamp(lastSyncedAt)}
            </Text>
          </View>
          <View style={styles.metaRow}>
            <Text style={[Typography.caption, { color: colors.textMuted }]}>
              National Prices Updated
            </Text>
            <Text style={[styles.metaValue, { color: colors.text }]}>
              {formatFreshnessTimestamp(catalogLastSyncAt)}
            </Text>
          </View>
          {trackedPricesCount !== null ? (
            <View style={styles.metaRow}>
              <Text style={[Typography.caption, { color: colors.textMuted }]}>
                Tracked Chain Prices
              </Text>
              <Text style={[styles.metaValue, { color: colors.accentSavings }]}>
                {trackedPricesCount} across 5 chains
              </Text>
            </View>
          ) : null}
          <View style={styles.metaRow}>
            <Text style={[Typography.caption, { color: colors.textMuted }]}>
              API Host
            </Text>
            <Text
              numberOfLines={1}
              style={[styles.metaValue, { color: colors.textSecondary }]}>
              {getApiBaseUrl()}
            </Text>
          </View>
        </View>

        <Pressable
          accessibilityRole="button"
          onPress={() => void probeBackendHealth()}
          style={({ pressed }) => [
            styles.primaryButton,
            {
              backgroundColor: pressed ? colors.primaryPressed : colors.primary,
            },
          ]}>
          <Text style={[styles.primaryButtonText, { color: colors.primaryText }]}>
            Refresh Connection & Freshness
          </Text>
        </Pressable>
      </View>

      {/* Quick Shortcuts */}
      <View style={styles.shortcutGrid}>
        <Pressable
          onPress={() => router.push('/(tabs)')}
          style={({ pressed }) => [
            styles.shortcutCard,
            cardShadow,
            {
              backgroundColor: colors.surface,
              borderColor: colors.border,
              opacity: pressed ? 0.85 : 1,
            },
          ]}>
          <IconSymbol name="tray.full.fill" size={24} color={colors.primary} />
          <Text style={[Typography.cardTitle, { color: colors.text }]}>
            Pantry
          </Text>
          <Text style={[Typography.caption, { color: colors.textSecondary }]}>
            Track staples & low stock
          </Text>
        </Pressable>

        <Pressable
          onPress={() => router.push('/(tabs)/explore')}
          style={({ pressed }) => [
            styles.shortcutCard,
            cardShadow,
            {
              backgroundColor: colors.surface,
              borderColor: colors.border,
              opacity: pressed ? 0.85 : 1,
            },
          ]}>
          <IconSymbol name="basket.fill" size={24} color={colors.primary} />
          <Text style={[Typography.cardTitle, { color: colors.text }]}>
            Basket
          </Text>
          <Text style={[Typography.caption, { color: colors.textSecondary }]}>
            Compare 5 national chains
          </Text>
        </Pressable>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: Spacing.lg,
    gap: Spacing.lg,
    paddingBottom: Spacing.xxl + 16,
  },
  heroCard: {
    borderRadius: Radii.xl,
    padding: Spacing.xl,
    borderWidth: 1,
    gap: Spacing.sm,
  },
  eyebrowBadge: {
    alignSelf: 'flex-start',
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: Radii.pill,
  },
  eyebrowText: {
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 0.7,
  },
  card: {
    borderRadius: Radii.lg,
    padding: Spacing.lg,
    borderWidth: 1,
    gap: Spacing.md,
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Spacing.sm,
  },
  segmentedTrack: {
    flexDirection: 'row',
    padding: 4,
    borderRadius: Radii.md,
    borderWidth: 1,
    gap: 4,
  },
  segmentPill: {
    flex: 1,
    paddingVertical: 10,
    borderRadius: Radii.sm,
    alignItems: 'center',
  },
  segmentLabel: {
    fontSize: 14,
    fontWeight: '700',
  },
  statusChip: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: Radii.pill,
  },
  metaList: {
    borderRadius: Radii.md,
    padding: Spacing.md,
    borderWidth: 1,
    gap: Spacing.sm,
  },
  metaRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: Spacing.md,
  },
  metaValue: {
    fontSize: 13,
    fontWeight: '600',
    flexShrink: 1,
    textAlign: 'right',
  },
  primaryButton: {
    paddingVertical: 13,
    borderRadius: Radii.md,
    alignItems: 'center',
  },
  primaryButtonText: {
    fontSize: 15,
    fontWeight: '700',
  },
  shortcutGrid: {
    flexDirection: 'row',
    gap: Spacing.md,
  },
  shortcutCard: {
    flex: 1,
    borderRadius: Radii.lg,
    padding: Spacing.lg,
    borderWidth: 1,
    gap: Spacing.xs,
  },
});
