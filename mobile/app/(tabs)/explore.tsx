/**
 * SmartBasket Optimizer Tab — Cached Comparison State, Included Retailers
 * Checklist & Smart Mode Split Cards (#27).
 *
 * - Data-Saving Cached State: displays the persisted last calculation
 *   immediately on tab switch with a "Last updated …" timestamp, making zero
 *   redundant API calls until the user taps Compare Prices from Pantry,
 *   toggles a retailer filter pill, or pulls to refresh.
 * - Included Retailers Checklist: multi-select pills for all 5 South African
 *   national chains (Shoprite, Checkers, Pick n Pay, SPAR, Woolworths Food),
 *   requiring at least 1 active chain.
 * - Warm Grocery Option B cards for the #1 Cheapest National Chain, Smart Mode
 *   split-basket savings breakdown, and Ranked National Chains (pure chain
 *   pricing only; zero branch names or stock availability text).
 */

import { useRouter } from 'expo-router';
import React, { useCallback, useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  View,
} from 'react-native';

import { IconSymbol } from '@/components/ui/IconSymbol';
import {
  getCardShadow,
  Radii,
  Spacing,
  Typography,
} from '@/constants/Theme';
import { useSyncStatus } from '@/context/SyncStatusContext';
import { useAppTheme } from '@/context/ThemeContext';
import { getActiveHomeId } from '@/services/api';
import {
  NATIONAL_RETAILER_CHAINS,
  syncAndCalculateSmartBasket,
} from '@/services/sync';

const DEFAULT_HOME_ID = '00000000-0000-4000-8000-000000000001';

function formatLastUpdated(iso: string | null): string {
  if (!iso) {
    return 'Not yet calculated';
  }
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) {
    return 'Recently updated';
  }
  return parsed.toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function SmartBasketScreen() {
  const router = useRouter();
  const { colors, colorScheme } = useAppTheme();
  const {
    latestComparison,
    lastCalculatedAt,
    selectedRetailerSlugs,
    isCacheHydrated,
    setLatestComparison,
    setSelectedRetailerSlugs,
    setSyncState,
  } = useSyncStatus();

  const homeId = getActiveHomeId() ?? DEFAULT_HOME_ID;
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [smartModeEnabled, setSmartModeEnabled] = useState<boolean>(true);

  const cardShadow = getCardShadow(colorScheme);

  const runComparison = useCallback(
    async (slugsToEvaluate: string[]) => {
      setIsRefreshing(true);
      setSyncState({ status: 'syncing' });
      try {
        const result = await syncAndCalculateSmartBasket(homeId, slugsToEvaluate);
        setLatestComparison(result, slugsToEvaluate);
        setSyncState({
          status: result.isLiveBackend ? 'synced' : 'offline',
        });
      } finally {
        setIsRefreshing(false);
      }
    },
    [homeId, setLatestComparison, setSyncState]
  );

  const handleToggleStore = (slug: string) => {
    const isSelected = selectedRetailerSlugs.includes(slug);
    let nextSlugs: string[];
    if (isSelected) {
      // Prevent unchecking the last remaining retailer (at least 1 must stay active)
      if (selectedRetailerSlugs.length <= 1) {
        return;
      }
      nextSlugs = selectedRetailerSlugs.filter((item) => item !== slug);
    } else {
      nextSlugs = [...selectedRetailerSlugs, slug];
    }

    setSelectedRetailerSlugs(nextSlugs);
    void runComparison(nextSlugs);
  };

  const calc = latestComparison?.calculation ?? null;
  const cheapestSingle = calc?.cheapest_single_store ?? null;
  const optimalSplit = calc?.optimal_split ?? null;
  const rankedStores = calc?.ranked_stores ?? [];

  const bestSingleTotal = cheapestSingle
    ? Number(cheapestSingle.total_price)
    : 0;

  return (
    <ScrollView
      style={{ backgroundColor: colors.background }}
      contentContainerStyle={styles.container}
      refreshControl={
        <RefreshControl
          refreshing={isRefreshing}
          onRefresh={() => void runComparison(selectedRetailerSlugs)}
          tintColor={colors.primary}
          colors={[colors.primary]}
        />
      }>
      {/* Top Header + Last Updated Telemetry */}
      <View style={styles.headerRow}>
        <View style={styles.headerTitleGroup}>
          <Text style={[Typography.title, { color: colors.text }]}>
            Basket Comparison
          </Text>
          <Text style={[Typography.caption, { color: colors.textSecondary }]}>
            {lastCalculatedAt
              ? `Last updated ${formatLastUpdated(lastCalculatedAt)} · Pull down to refresh`
              : 'Tap Compare Prices to evaluate your active pantry items'}
          </Text>
        </View>

        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Refresh basket price comparison"
          onPress={() => void runComparison(selectedRetailerSlugs)}
          disabled={isRefreshing}
          style={({ pressed }) => [
            styles.refreshChip,
            {
              backgroundColor: colors.surface,
              borderColor: colors.border,
              opacity: pressed || isRefreshing ? 0.7 : 1,
            },
          ]}>
          {isRefreshing ? (
            <ActivityIndicator size="small" color={colors.primary} />
          ) : (
            <IconSymbol
              name="arrow.triangle.2.circlepath"
              size={16}
              color={colors.primary}
            />
          )}
          <Text style={[styles.refreshChipText, { color: colors.text }]}>
            {isRefreshing ? 'Updating…' : 'Refresh'}
          </Text>
        </Pressable>
      </View>

      {/* Included Retailers Multi-Select Checklist */}
      <View
        style={[
          styles.card,
          cardShadow,
          {
            backgroundColor: colors.surface,
            borderColor: colors.border,
          },
        ]}>
        <View style={styles.cardHeaderRow}>
          <Text style={[Typography.cardTitle, { color: colors.text }]}>
            Included Retailers
          </Text>
          <View
            style={[
              styles.countBadge,
              { backgroundColor: colors.primaryMuted },
            ]}>
            <Text style={[Typography.badge, { color: colors.primary }]}>
              {selectedRetailerSlugs.length} of {NATIONAL_RETAILER_CHAINS.length}
            </Text>
          </View>
        </View>

        <Text style={[Typography.caption, { color: colors.textSecondary }]}>
          Select the South African national chains to include in single-chain
          and Smart Mode comparisons (minimum 1).
        </Text>

        <View style={styles.retailerPillWrap}>
          {NATIONAL_RETAILER_CHAINS.map((chain) => {
            const isChecked = selectedRetailerSlugs.includes(chain.slug);
            const isLastRemaining =
              isChecked && selectedRetailerSlugs.length === 1;

            return (
              <Pressable
                key={chain.slug}
                accessibilityRole="checkbox"
                accessibilityState={{ checked: isChecked, disabled: isLastRemaining }}
                onPress={() => handleToggleStore(chain.slug)}
                style={({ pressed }) => [
                  styles.retailerPill,
                  {
                    backgroundColor: isChecked
                      ? colors.primaryMuted
                      : colors.surfaceElevated,
                    borderColor: isChecked ? colors.primary : colors.border,
                    opacity: pressed ? 0.78 : isLastRemaining ? 0.92 : 1,
                  },
                ]}>
                <View
                  style={[
                    styles.pillCheckCircle,
                    {
                      backgroundColor: isChecked
                        ? colors.primary
                        : 'transparent',
                      borderColor: isChecked
                        ? colors.primary
                        : colors.textMuted,
                    },
                  ]}>
                  {isChecked ? (
                    <IconSymbol
                      name="checkmark"
                      size={11}
                      color={colors.primaryText}
                    />
                  ) : null}
                </View>
                <Text
                  style={[
                    styles.retailerPillText,
                    {
                      color: isChecked ? colors.primary : colors.textSecondary,
                    },
                  ]}>
                  {chain.name}
                </Text>
              </Pressable>
            );
          })}
        </View>
      </View>

      {/* Empty / First-Run State (Zero Automatic Fetches on Tab Switch) */}
      {!calc ? (
        <View
          style={[
            styles.emptyCard,
            cardShadow,
            {
              backgroundColor: colors.surface,
              borderColor: colors.border,
            },
          ]}>
          <View
            style={[
              styles.emptyIconCircle,
              { backgroundColor: colors.primaryMuted },
            ]}>
            <IconSymbol name="basket.fill" size={28} color={colors.primary} />
          </View>
          <Text style={[Typography.subtitle, { color: colors.text }]}>
            {isCacheHydrated
              ? 'Ready to compare prices'
              : 'Loading cached comparison…'}
          </Text>
          <Text
            style={[
              Typography.body,
              styles.emptyCopy,
              { color: colors.textSecondary },
            ]}>
            Your Basket tab caches results to save mobile data. Tap Compare
            Prices from your Pantry or calculate your selected national chains
            below.
          </Text>

          <View style={styles.emptyActions}>
            <Pressable
              onPress={() => void runComparison(selectedRetailerSlugs)}
              disabled={isRefreshing}
              style={({ pressed }) => [
                styles.primaryCta,
                {
                  backgroundColor: pressed
                    ? colors.primaryPressed
                    : colors.primary,
                },
              ]}>
              <Text
                style={[styles.primaryCtaText, { color: colors.primaryText }]}>
                {isRefreshing ? 'Calculating…' : 'Calculate Basket Now'}
              </Text>
            </Pressable>

            <Pressable
              onPress={() => router.push('/(tabs)')}
              style={[
                styles.secondaryCta,
                {
                  backgroundColor: colors.surfaceElevated,
                  borderColor: colors.border,
                },
              ]}>
              <Text style={[styles.secondaryCtaText, { color: colors.text }]}>
                Back to Pantry
              </Text>
            </Pressable>
          </View>
        </View>
      ) : (
        <>
          {/* #1 Cheapest National Chain Hero Card */}
          {cheapestSingle ? (
            <View
              style={[
                styles.heroCard,
                cardShadow,
                {
                  backgroundColor: colors.surface,
                  borderColor: colors.primary,
                },
              ]}>
              <View style={styles.cardHeaderRow}>
                <View
                  style={[
                    styles.heroBadge,
                    { backgroundColor: colors.primaryMuted },
                  ]}>
                  <Text style={[Typography.badge, { color: colors.primary }]}>
                    #1 CHEAPEST NATIONAL CHAIN
                  </Text>
                </View>
                <Text style={[Typography.caption, { color: colors.textMuted }]}>
                  {calc.total_items_requested} item
                  {calc.total_items_requested === 1 ? '' : 's'}
                </Text>
              </View>

              <View style={styles.heroPriceRow}>
                <Text style={[Typography.title, { color: colors.text, flex: 1 }]}>
                  {cheapestSingle.retailer_name}
                </Text>
                <Text style={[Typography.hero, { color: colors.primary }]}>
                  R {cheapestSingle.total_price}
                </Text>
              </View>

              <View
                style={[
                  styles.lineItemsBox,
                  {
                    backgroundColor: colors.surfaceElevated,
                    borderColor: colors.borderSubtle,
                  },
                ]}>
                {cheapestSingle.items.map((item) => (
                  <View key={item.product_id} style={styles.lineItemRow}>
                    <View style={styles.lineItemInfo}>
                      <Text
                        numberOfLines={1}
                        style={[Typography.bodySemiBold, { color: colors.text }]}>
                        {item.product_name}
                      </Text>
                      <Text
                        style={[Typography.caption, { color: colors.textMuted }]}>
                        Qty {item.quantity} × R {item.unit_price}
                      </Text>
                    </View>
                    <View style={styles.lineItemPriceGroup}>
                      {item.is_promotional ? (
                        <View
                          style={[
                            styles.promoTag,
                            { backgroundColor: colors.statusLowBg },
                          ]}>
                          <Text
                            style={[
                              Typography.badge,
                              { color: colors.statusLow },
                            ]}>
                            PROMO
                          </Text>
                        </View>
                      ) : null}
                      <Text
                        style={[Typography.bodySemiBold, { color: colors.text }]}>
                        R {item.subtotal}
                      </Text>
                    </View>
                  </View>
                ))}
              </View>

              <Text style={[Typography.caption, { color: colors.textMuted }]}>
                {latestComparison?.isLiveBackend
                  ? 'Live national chain pricing via SmartBasket API'
                  : 'Cached offline national chain catalog'}
              </Text>
            </View>
          ) : null}

          {/* Smart Mode (Split Basket) Card */}
          <View
            style={[
              styles.card,
              cardShadow,
              {
                backgroundColor: colors.surface,
                borderColor: colors.border,
              },
            ]}>
            <View style={styles.cardHeaderRow}>
              <View style={styles.smartTitleGroup}>
                <Text style={[Typography.subtitle, { color: colors.text }]}>
                  Smart Mode Split
                </Text>
                <Text
                  style={[Typography.caption, { color: colors.textSecondary }]}>
                  Optimal per-item split across selected chains
                </Text>
              </View>
              <Switch
                value={smartModeEnabled}
                onValueChange={setSmartModeEnabled}
                trackColor={{
                  false: colors.border,
                  true: colors.primaryMuted,
                }}
                thumbColor={
                  smartModeEnabled ? colors.primary : colors.textMuted
                }
              />
            </View>

            {smartModeEnabled ? (
              optimalSplit && optimalSplit.cheaper_than_single_store ? (
                <View style={styles.splitContent}>
                  <View
                    style={[
                      styles.savingsHeroRow,
                      {
                        backgroundColor: colors.accentSavingsBg,
                        borderColor: colors.accentSavings,
                      },
                    ]}>
                    <View style={styles.savingsCopy}>
                      <Text
                        style={[
                          Typography.badge,
                          { color: colors.accentSavings },
                        ]}>
                        SPLIT ACROSS {optimalSplit.stores.length} CHAINS
                      </Text>
                      <Text
                        style={[
                          Typography.subtitle,
                          { color: colors.text, marginTop: 2 },
                        ]}>
                        Save R {optimalSplit.savings_amount} (
                        {optimalSplit.savings_percentage}%)
                      </Text>
                    </View>
                    <View style={styles.splitTotalBox}>
                      <Text
                        style={[Typography.caption, { color: colors.textMuted }]}>
                        Split Total
                      </Text>
                      <Text
                        style={[
                          Typography.title,
                          { color: colors.accentSavings },
                        ]}>
                        R {optimalSplit.total_price}
                      </Text>
                    </View>
                  </View>

                  {optimalSplit.stores.map((alloc) => (
                    <View
                      key={alloc.store_id}
                      style={[
                        styles.splitChainCard,
                        {
                          backgroundColor: colors.surfaceElevated,
                          borderColor: colors.borderSubtle,
                        },
                      ]}>
                      <View style={styles.cardHeaderRow}>
                        <Text
                          style={[
                            Typography.cardTitle,
                            { color: colors.primary },
                          ]}>
                          {alloc.retailer_name}
                        </Text>
                        <Text
                          style={[
                            Typography.bodySemiBold,
                            { color: colors.text },
                          ]}>
                          R {alloc.subtotal}
                        </Text>
                      </View>
                      {alloc.items.map((item) => (
                        <View
                          key={`${alloc.store_id}-${item.product_id}`}
                          style={styles.splitItemRow}>
                          <Text
                            numberOfLines={1}
                            style={[
                              Typography.caption,
                              { color: colors.textSecondary, flex: 1 },
                            ]}>
                            • {item.product_name} ({item.quantity})
                          </Text>
                          <View style={styles.lineItemPriceGroup}>
                            {item.is_promotional ? (
                              <View
                                style={[
                                  styles.promoTag,
                                  { backgroundColor: colors.statusLowBg },
                                ]}>
                                <Text
                                  style={[
                                    Typography.badge,
                                    { color: colors.statusLow },
                                  ]}>
                                  PROMO
                                </Text>
                              </View>
                            ) : null}
                            <Text
                              style={[
                                Typography.caption,
                                { color: colors.text, fontWeight: '700' },
                              ]}>
                              R {item.subtotal}
                            </Text>
                          </View>
                        </View>
                      ))}
                    </View>
                  ))}
                </View>
              ) : (
                <View
                  style={[
                    styles.optimalNotice,
                    {
                      backgroundColor: colors.statusOkBg,
                      borderColor: colors.borderSubtle,
                    },
                  ]}>
                  <IconSymbol
                    name="checkmark.circle.fill"
                    size={18}
                    color={colors.statusOk}
                  />
                  <Text
                    style={[
                      Typography.caption,
                      { color: colors.statusOk, flex: 1 },
                    ]}>
                    {selectedRetailerSlugs.length < 2
                      ? 'Select 2 or more chains above to compare multi-chain split savings.'
                      : 'Single-chain shopping is already optimal for your current basket.'}
                  </Text>
                </View>
              )
            ) : null}
          </View>

          {/* Ranked National Chains Comparison Card */}
          <View
            style={[
              styles.card,
              cardShadow,
              {
                backgroundColor: colors.surface,
                borderColor: colors.border,
              },
            ]}>
            <View style={styles.cardHeaderRow}>
              <Text style={[Typography.subtitle, { color: colors.text }]}>
                All Selected Chains
              </Text>
              <Text style={[Typography.caption, { color: colors.textMuted }]}>
                Lowest total first
              </Text>
            </View>

            <View style={styles.rankedStack}>
              {rankedStores.map((store, idx) => {
                const isBest = idx === 0;
                const diff = Math.max(
                  0,
                  Number(store.total_price) - bestSingleTotal
                );

                return (
                  <View
                    key={store.store_id}
                    style={[
                      styles.rankedRow,
                      {
                        backgroundColor: isBest
                          ? colors.primaryMuted
                          : colors.surfaceElevated,
                        borderColor: isBest
                          ? colors.primary
                          : colors.borderSubtle,
                      },
                    ]}>
                    <View
                      style={[
                        styles.rankPill,
                        {
                          backgroundColor: isBest
                            ? colors.primary
                            : colors.surfaceMuted,
                        },
                      ]}>
                      <Text
                        style={[
                          styles.rankPillText,
                          {
                            color: isBest
                              ? colors.primaryText
                              : colors.textSecondary,
                          },
                        ]}>
                        #{idx + 1}
                      </Text>
                    </View>

                    <View style={styles.rankedChainInfo}>
                      <Text
                        style={[Typography.bodySemiBold, { color: colors.text }]}>
                        {store.retailer_name}
                      </Text>
                      <Text
                        style={[Typography.caption, { color: colors.textMuted }]}>
                        {isBest
                          ? 'Best single-chain total'
                          : `+R ${diff.toFixed(2)} vs. #1 chain`}
                      </Text>
                    </View>

                    <Text
                      style={[
                        Typography.cardTitle,
                        { color: isBest ? colors.primary : colors.text },
                      ]}>
                      R {store.total_price}
                    </Text>
                  </View>
                );
              })}
            </View>
          </View>
        </>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: Spacing.lg,
    paddingBottom: Spacing.xxl + 16,
    gap: Spacing.md,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Spacing.sm,
  },
  headerTitleGroup: {
    flex: 1,
    gap: 2,
  },
  refreshChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: Radii.pill,
    borderWidth: 1,
  },
  refreshChipText: {
    fontSize: 13,
    fontWeight: '700',
  },
  card: {
    borderRadius: Radii.lg,
    padding: Spacing.lg,
    borderWidth: 1,
    gap: Spacing.md,
  },
  heroCard: {
    borderRadius: Radii.xl,
    padding: Spacing.lg,
    borderWidth: 1.5,
    gap: Spacing.md,
  },
  cardHeaderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Spacing.sm,
  },
  countBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: Radii.pill,
  },
  retailerPillWrap: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.sm,
  },
  retailerPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 7,
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: Radii.pill,
    borderWidth: 1,
  },
  pillCheckCircle: {
    width: 18,
    height: 18,
    borderRadius: Radii.pill,
    borderWidth: 1.5,
    alignItems: 'center',
    justifyContent: 'center',
  },
  retailerPillText: {
    fontSize: 13,
    fontWeight: '700',
  },
  heroBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: Radii.pill,
  },
  heroPriceRow: {
    flexDirection: 'row',
    alignItems: 'baseline',
    justifyContent: 'space-between',
    gap: Spacing.md,
  },
  lineItemsBox: {
    borderRadius: Radii.md,
    padding: Spacing.md,
    borderWidth: 1,
    gap: Spacing.sm + 2,
  },
  lineItemRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Spacing.sm,
  },
  lineItemInfo: {
    flex: 1,
    gap: 1,
  },
  lineItemPriceGroup: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  promoTag: {
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: Radii.pill,
  },
  smartTitleGroup: {
    flex: 1,
    gap: 2,
  },
  splitContent: {
    gap: Spacing.sm + 2,
  },
  savingsHeroRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Spacing.md,
    padding: Spacing.md,
    borderRadius: Radii.md,
    borderWidth: 1,
  },
  savingsCopy: {
    flex: 1,
  },
  splitTotalBox: {
    alignItems: 'flex-end',
  },
  splitChainCard: {
    borderRadius: Radii.md,
    padding: Spacing.md,
    borderWidth: 1,
    gap: Spacing.xs + 2,
  },
  splitItemRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Spacing.sm,
  },
  optimalNotice: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
    padding: Spacing.md,
    borderRadius: Radii.md,
    borderWidth: 1,
  },
  rankedStack: {
    gap: Spacing.sm,
  },
  rankedRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.md,
    paddingHorizontal: Spacing.md,
    paddingVertical: 12,
    borderRadius: Radii.md,
    borderWidth: 1,
  },
  rankPill: {
    width: 34,
    height: 28,
    borderRadius: Radii.sm,
    alignItems: 'center',
    justifyContent: 'center',
  },
  rankPillText: {
    fontSize: 13,
    fontWeight: '800',
  },
  rankedChainInfo: {
    flex: 1,
    gap: 1,
  },
  emptyCard: {
    borderRadius: Radii.xl,
    padding: Spacing.xxl,
    borderWidth: 1,
    alignItems: 'center',
    gap: Spacing.md,
  },
  emptyIconCircle: {
    width: 56,
    height: 56,
    borderRadius: Radii.pill,
    alignItems: 'center',
    justifyContent: 'center',
  },
  emptyCopy: {
    textAlign: 'center',
  },
  emptyActions: {
    width: '100%',
    gap: Spacing.sm,
    marginTop: Spacing.xs,
  },
  primaryCta: {
    paddingVertical: 14,
    borderRadius: Radii.pill,
    alignItems: 'center',
  },
  primaryCtaText: {
    fontSize: 15,
    fontWeight: '800',
  },
  secondaryCta: {
    paddingVertical: 12,
    borderRadius: Radii.pill,
    borderWidth: 1,
    alignItems: 'center',
  },
  secondaryCtaText: {
    fontSize: 14,
    fontWeight: '700',
  },
});
