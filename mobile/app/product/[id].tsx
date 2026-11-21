/**
 * Clean Cross-Chain Product Price Comparison Sheet (#28).
 *
 * Lightweight, scannable bottom-sheet modal styled in the Warm Grocery theme
 * displaying current prices across the 5 South African national supermarket
 * chains (Shoprite, Checkers, Pick n Pay, SPAR, Woolworths Food), sorted
 * cheapest-first with an emerald "Best Price" badge and promotional pills.
 *
 * Strictly consumer-focused: no price history charts, inflation metrics,
 * deal-veracity scores, branch locations, or inventory/stock language.
 */

import { useLocalSearchParams, useRouter } from 'expo-router';
import React, { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { IconSymbol } from '@/components/ui/IconSymbol';
import {
  getCardShadow,
  Radii,
  Spacing,
  Typography,
} from '@/constants/Theme';
import { useAppTheme } from '@/context/ThemeContext';
import {
  getProductCrossChainPrices,
  type ProductCrossChainPriceResult,
} from '@/services/sync';

function formatPackageSize(unitSize?: string, unitType?: string): string | null {
  if (!unitSize || !unitType) {
    return null;
  }
  const numeric = Number(unitSize);
  const cleanNumber = Number.isFinite(numeric)
    ? numeric % 1 === 0
      ? String(Math.trunc(numeric))
      : String(numeric)
    : unitSize;

  if (unitType === 'unit') {
    return numeric === 1 ? '1 unit' : `${cleanNumber}pk`;
  }
  return `${cleanNumber}${unitType}`;
}

export default function ProductPriceSheetScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { colors, colorScheme } = useAppTheme();
  const params = useLocalSearchParams<{ id?: string; name?: string }>();

  const productId = typeof params.id === 'string' ? params.id : '';
  const fallbackName = typeof params.name === 'string' ? params.name : undefined;

  const [data, setData] = useState<ProductCrossChainPriceResult | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const cardShadow = getCardShadow(colorScheme);

  const loadPrices = useCallback(async () => {
    if (!productId) {
      setErrorMessage('Invalid product reference.');
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const result = await getProductCrossChainPrices(productId, fallbackName);
      setData(result);
    } catch {
      setErrorMessage('Unable to load chain prices right now.');
    } finally {
      setIsLoading(false);
    }
  }, [productId, fallbackName]);

  useEffect(() => {
    void loadPrices();
  }, [loadPrices]);

  const product = data?.product ?? null;
  const displayTitle = data?.productName ?? fallbackName ?? 'Product Prices';
  const packLabel = formatPackageSize(product?.unit_size, product?.unit_type);
  const subtitleParts = [product?.brand ?? null, packLabel].filter(Boolean);

  const prices = data?.prices ?? [];
  const cheapestPrice = prices.length > 0 ? Number(prices[0].price) : 0;

  return (
    <View
      style={[
        styles.sheetContainer,
        {
          backgroundColor: colors.background,
          paddingTop: Math.max(insets.top, Spacing.md),
          paddingBottom: Math.max(insets.bottom, Spacing.lg),
        },
      ]}>
      {/* Bottom-Sheet Drag Handle & Close Header */}
      <View style={styles.handleRow}>
        <View
          style={[styles.grabHandle, { backgroundColor: colors.border }]}
        />
      </View>

      <View style={styles.topBar}>
        <Text style={[Typography.badge, { color: colors.primary }]}>
          CROSS-CHAIN PRICE CHECK
        </Text>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Close product price sheet"
          onPress={() => router.back()}
          style={({ pressed }) => [
            styles.closeButton,
            {
              backgroundColor: colors.surfaceElevated,
              borderColor: colors.border,
              opacity: pressed ? 0.75 : 1,
            },
          ]}>
          <IconSymbol name="xmark" size={16} color={colors.text} />
        </Pressable>
      </View>

      <ScrollView contentContainerStyle={styles.scrollContent}>
        {/* Product Metadata Header Card */}
        <View
          style={[
            styles.headerCard,
            cardShadow,
            {
              backgroundColor: colors.surface,
              borderColor: colors.border,
            },
          ]}>
          <Text style={[Typography.title, { color: colors.text }]}>
            {displayTitle}
          </Text>
          {subtitleParts.length > 0 ? (
            <Text style={[Typography.bodySemiBold, { color: colors.textSecondary }]}>
              {subtitleParts.join(' · ')}
            </Text>
          ) : null}
          {product?.barcode ? (
            <Text style={[Typography.caption, { color: colors.textMuted }]}>
              Barcode {product.barcode}
            </Text>
          ) : null}
        </View>

        {/* Cross-Chain Ranked Price List */}
        {isLoading ? (
          <View
            style={[
              styles.stateCard,
              {
                backgroundColor: colors.surface,
                borderColor: colors.border,
              },
            ]}>
            <ActivityIndicator size="large" color={colors.primary} />
            <Text style={[Typography.body, { color: colors.textSecondary }]}>
              Checking prices across all 5 national chains…
            </Text>
          </View>
        ) : errorMessage || prices.length === 0 ? (
          <View
            style={[
              styles.stateCard,
              {
                backgroundColor: colors.surface,
                borderColor: colors.border,
              },
            ]}>
            <Text style={[Typography.subtitle, { color: colors.text }]}>
              {errorMessage ?? 'No chain prices found'}
            </Text>
            <Text
              style={[
                Typography.body,
                styles.centeredCopy,
                { color: colors.textSecondary },
              ]}>
              This item doesn&apos;t have comparable national chain prices right
              now.
            </Text>
            <Pressable
              onPress={() => void loadPrices()}
              style={[
                styles.retryButton,
                { backgroundColor: colors.primary },
              ]}>
              <Text
                style={[styles.retryButtonText, { color: colors.primaryText }]}>
                Try Again
              </Text>
            </Pressable>
          </View>
        ) : (
          <View
            style={[
              styles.listCard,
              cardShadow,
              {
                backgroundColor: colors.surface,
                borderColor: colors.border,
              },
            ]}>
            <View style={styles.listHeader}>
              <Text style={[Typography.cardTitle, { color: colors.text }]}>
                Current National Chain Prices
              </Text>
              <Text style={[Typography.caption, { color: colors.textMuted }]}>
                Cheapest first
              </Text>
            </View>

            <View style={styles.priceRows}>
              {prices.map((entry, idx) => {
                const isBest = idx === 0;
                const priceNum = Number(entry.price);
                const diff = Math.max(0, priceNum - cheapestPrice);

                return (
                  <View
                    key={entry.id}
                    style={[
                      styles.priceRow,
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
                        styles.rankBadge,
                        {
                          backgroundColor: isBest
                            ? colors.primary
                            : colors.surfaceMuted,
                        },
                      ]}>
                      <Text
                        style={[
                          styles.rankBadgeText,
                          {
                            color: isBest
                              ? colors.primaryText
                              : colors.textSecondary,
                          },
                        ]}>
                        #{idx + 1}
                      </Text>
                    </View>

                    <View style={styles.chainMeta}>
                      <View style={styles.chainNameLine}>
                        <Text
                          style={[
                            Typography.bodySemiBold,
                            { color: colors.text },
                          ]}>
                          {entry.retailer_name}
                        </Text>
                        {isBest ? (
                          <View
                            style={[
                              styles.bestBadge,
                              { backgroundColor: colors.primary },
                            ]}>
                            <Text
                              style={[
                                Typography.badge,
                                { color: colors.primaryText },
                              ]}>
                              Best Price
                            </Text>
                          </View>
                        ) : null}
                      </View>

                      <View style={styles.subBadgeLine}>
                        {entry.is_promotional ? (
                          <View
                            style={[
                              styles.promoPill,
                              { backgroundColor: colors.statusLowBg },
                            ]}>
                            <Text
                              style={[
                                Typography.badge,
                                { color: colors.statusLow },
                              ]}>
                              Promo Special
                            </Text>
                          </View>
                        ) : null}
                        <Text
                          style={[
                            Typography.caption,
                            { color: colors.textMuted },
                          ]}>
                          {isBest
                            ? 'Lowest national price'
                            : `+R ${diff.toFixed(2)} more`}
                        </Text>
                      </View>
                    </View>

                    <Text
                      style={[
                        Typography.subtitle,
                        { color: isBest ? colors.primary : colors.text },
                      ]}>
                      R {entry.price}
                    </Text>
                  </View>
                );
              })}
            </View>

            <Text style={[Typography.caption, { color: colors.textMuted }]}>
              {data?.isLiveBackend
                ? 'Live national chain pricing · SmartBasket Catalog'
                : 'Offline cached national chain pricing'}
            </Text>
          </View>
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  sheetContainer: {
    flex: 1,
  },
  handleRow: {
    alignItems: 'center',
    paddingBottom: Spacing.sm,
  },
  grabHandle: {
    width: 40,
    height: 4,
    borderRadius: Radii.pill,
  },
  topBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: Spacing.lg,
    paddingBottom: Spacing.sm,
  },
  closeButton: {
    width: 34,
    height: 34,
    borderRadius: Radii.pill,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  scrollContent: {
    padding: Spacing.lg,
    paddingTop: Spacing.xs,
    gap: Spacing.md,
  },
  headerCard: {
    borderRadius: Radii.xl,
    padding: Spacing.lg,
    borderWidth: 1,
    gap: Spacing.xs,
  },
  listCard: {
    borderRadius: Radii.xl,
    padding: Spacing.lg,
    borderWidth: 1,
    gap: Spacing.md,
  },
  listHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Spacing.sm,
  },
  priceRows: {
    gap: Spacing.sm,
  },
  priceRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.md,
    paddingHorizontal: Spacing.md,
    paddingVertical: 13,
    borderRadius: Radii.md,
    borderWidth: 1,
  },
  rankBadge: {
    width: 32,
    height: 28,
    borderRadius: Radii.sm,
    alignItems: 'center',
    justifyContent: 'center',
  },
  rankBadgeText: {
    fontSize: 13,
    fontWeight: '800',
  },
  chainMeta: {
    flex: 1,
    gap: 4,
  },
  chainNameLine: {
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: 6,
  },
  bestBadge: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: Radii.pill,
  },
  subBadgeLine: {
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: 6,
  },
  promoPill: {
    paddingHorizontal: 7,
    paddingVertical: 2,
    borderRadius: Radii.pill,
  },
  stateCard: {
    borderRadius: Radii.xl,
    padding: Spacing.xxl,
    borderWidth: 1,
    alignItems: 'center',
    gap: Spacing.md,
  },
  centeredCopy: {
    textAlign: 'center',
  },
  retryButton: {
    paddingHorizontal: Spacing.xl,
    paddingVertical: 12,
    borderRadius: Radii.pill,
  },
  retryButtonText: {
    fontSize: 14,
    fontWeight: '800',
  },
});
