import React, { useCallback, useEffect, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Switch, View } from 'react-native';

import { ThemedText } from '@/components/ThemedText';
import { ThemedView } from '@/components/ThemedView';
import { getActiveHomeId } from '@/services/api';
import {
  HouseholdBasketComparisonResult,
  NATIONAL_RETAILER_CHAINS,
  syncAndCalculateSmartBasket,
} from '@/services/sync';

const DEFAULT_HOME_ID = '00000000-0000-4000-8000-000000000001';
const ALL_RETAILER_SLUGS = NATIONAL_RETAILER_CHAINS.map((c) => c.slug);

export default function SmartBasketScreen() {
  const homeId = getActiveHomeId() ?? DEFAULT_HOME_ID;
  const [comparison, setComparison] =
    useState<HouseholdBasketComparisonResult | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [smartModeEnabled, setSmartModeEnabled] = useState<boolean>(true);
  const [selectedSlugs, setSelectedSlugs] =
    useState<string[]>(ALL_RETAILER_SLUGS);

  const refreshComparison = useCallback(
    async (slugsToEvaluate: string[]) => {
      setIsLoading(true);
      const result = await syncAndCalculateSmartBasket(homeId, slugsToEvaluate);
      setComparison(result);
      setIsLoading(false);
    },
    [homeId]
  );

  useEffect(() => {
    void refreshComparison(selectedSlugs);
  }, [refreshComparison, selectedSlugs]);

  const handleToggleStore = (slug: string) => {
    setSelectedSlugs((prev) => {
      const isSelected = prev.includes(slug);
      if (isSelected) {
        // Prevent unchecking the last remaining store (at least 1 must stay selected)
        if (prev.length <= 1) {
          return prev;
        }
        return prev.filter((item) => item !== slug);
      }
      return [...prev, slug];
    });
  };

  const calc = comparison?.calculation;
  const cheapestSingle = calc?.cheapest_single_store;
  const optimalSplit = calc?.optimal_split;
  const rankedStores = calc?.ranked_stores ?? [];

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <ThemedView style={styles.headerCard}>
        <ThemedText type="title">SmartBasket Optimizer</ThemedText>
        <ThemedText style={styles.subtitleText}>
          Multi-chain price comparison fed by low & finished household pantry
          staples
        </ThemedText>

        <View style={styles.metaRow}>
          <ThemedText style={styles.metaText}>
            Replenishment Items: {calc?.total_items_requested ?? 0}
          </ThemedText>
          <ThemedText style={styles.metaText}>
            Source:{' '}
            {comparison?.isLiveBackend
              ? 'Live FastAPI (/baskets/calculate)'
              : 'Offline Cached Catalog'}
          </ThemedText>
        </View>

        <Pressable
          style={styles.refreshButton}
          onPress={() => void refreshComparison(selectedSlugs)}
          disabled={isLoading}>
          <ThemedText style={styles.refreshButtonText}>
            {isLoading
              ? 'Calculating Best Prices...'
              : 'Recalculate Selected Chains'}
          </ThemedText>
        </Pressable>
      </ThemedView>

      <ThemedView style={styles.checklistCard}>
        <View style={styles.checklistHeader}>
          <ThemedText type="subtitle">Included Stores</ThemedText>
          <ThemedText style={styles.checklistCount}>
            {selectedSlugs.length} of {NATIONAL_RETAILER_CHAINS.length} selected
          </ThemedText>
        </View>
        <ThemedText style={styles.retailerSub}>
          Choose which national chains to compare and include in Smart Mode
          splits:
        </ThemedText>

        <View style={styles.pillsContainer}>
          {NATIONAL_RETAILER_CHAINS.map((chain) => {
            const isChecked = selectedSlugs.includes(chain.slug);
            const isLastRemaining = isChecked && selectedSlugs.length === 1;
            return (
              <Pressable
                key={chain.slug}
                onPress={() => handleToggleStore(chain.slug)}
                style={[
                  styles.storePill,
                  isChecked ? styles.storePillSelected : styles.storePillUnselected,
                  isLastRemaining && styles.storePillLocked,
                ]}>
                <ThemedText
                  style={[
                    styles.storePillText,
                    isChecked
                      ? styles.storePillTextSelected
                      : styles.storePillTextUnselected,
                  ]}>
                  {isChecked ? '✓ ' : '+ '}
                  {chain.name}
                </ThemedText>
              </Pressable>
            );
          })}
        </View>
        {selectedSlugs.length === 1 && (
          <ThemedText style={styles.minStoreHint}>
            At least 1 retailer must remain selected for comparison.
          </ThemedText>
        )}
      </ThemedView>

      {cheapestSingle && (
        <ThemedView style={styles.highlightCard}>
          <ThemedText style={styles.sectionTag}>
            CHEAPEST NATIONAL CHAIN
          </ThemedText>
          <View style={styles.priceRow}>
            <View style={styles.storeInfo}>
              <ThemedText type="subtitle">
                {cheapestSingle.retailer_name}
              </ThemedText>
              <ThemedText style={styles.retailerSub}>
                National Chain Pricing · {cheapestSingle.total_items_count}{' '}
                basket {cheapestSingle.total_items_count === 1 ? 'item' : 'items'}
              </ThemedText>
            </View>
            <ThemedText type="title" style={styles.priceHighlight}>
              R{cheapestSingle.total_price}
            </ThemedText>
          </View>
        </ThemedView>
      )}

      {calc && (
        <ThemedView style={styles.splitCard}>
          <View style={styles.smartModeToggleRow}>
            <View style={styles.smartModeTitleGroup}>
              <ThemedText style={styles.splitTag}>
                SMART MODE (SPLIT BASKET)
              </ThemedText>
              <ThemedText style={styles.retailerSub}>
                Optimal split across your {selectedSlugs.length} selected{' '}
                {selectedSlugs.length === 1 ? 'chain' : 'chains'}
              </ThemedText>
            </View>
            <Switch
              value={smartModeEnabled}
              onValueChange={setSmartModeEnabled}
              trackColor={{ false: '#555558', true: '#0A7EA4' }}
              thumbColor="#FFFFFF"
            />
          </View>

          {smartModeEnabled ? (
            optimalSplit && optimalSplit.cheaper_than_single_store ? (
              <View style={styles.splitBody}>
                <View style={styles.splitHeader}>
                  <ThemedText type="subtitle">
                    Smart Mode ({optimalSplit.stores.length}-Chain Split)
                  </ThemedText>
                  <ThemedText style={styles.savingsBadge}>
                    Save R{optimalSplit.savings_amount} (
                    {optimalSplit.savings_percentage}%) vs. #1{' '}
                    {cheapestSingle?.retailer_name ?? 'Chain'}
                  </ThemedText>
                </View>

                <View style={styles.priceRow}>
                  <ThemedText style={styles.retailerSub}>
                    Combined split total (was R
                    {cheapestSingle?.total_price ?? optimalSplit.total_price})
                  </ThemedText>
                  <ThemedText type="title" style={styles.splitPrice}>
                    R{optimalSplit.total_price}
                  </ThemedText>
                </View>

                {optimalSplit.stores.map((allocation) => (
                  <View key={allocation.store_id} style={styles.allocationBox}>
                    <View style={styles.allocationHeader}>
                      <ThemedText type="defaultSemiBold">
                        {allocation.retailer_name}
                      </ThemedText>
                      <ThemedText type="defaultSemiBold">
                        Subtotal: R{allocation.subtotal}
                      </ThemedText>
                    </View>
                    {allocation.items.map((item) => (
                      <ThemedText
                        key={item.product_id}
                        style={styles.lineItemText}>
                        • {item.product_name} ({item.quantity}x @ R
                        {item.unit_price}) = R{item.subtotal}
                        {item.is_promotional ? ' [PROMO]' : ''}
                      </ThemedText>
                    ))}
                  </View>
                ))}
              </View>
            ) : (
              <View style={styles.singleOptimalBadge}>
                <ThemedText style={styles.singleOptimalText}>
                  Single-store shopping at{' '}
                  {cheapestSingle?.retailer_name ?? 'the #1 chain'} is already
                  optimal for every item among your selected stores.
                </ThemedText>
              </View>
            )
          ) : (
            <ThemedText style={styles.retailerSub}>
              Enable Smart Mode to inspect multi-chain split recommendations and
              potential savings.
            </ThemedText>
          )}
        </ThemedView>
      )}

      <ThemedView style={styles.rankingsSection}>
        <ThemedText type="subtitle">
          National Retailers Ranked ({rankedStores.length})
        </ThemedText>
        {rankedStores.map((store, index) => (
          <ThemedView key={store.store_id} style={styles.storeRow}>
            <View style={styles.rankInfo}>
              <ThemedText type="defaultSemiBold">
                #{index + 1} {store.retailer_name}
              </ThemedText>
              <ThemedText style={styles.retailerSub}>
                National chain basket total
              </ThemedText>
            </View>
            <ThemedText type="defaultSemiBold" style={styles.storeTotalText}>
              R{store.total_price}
            </ThemedText>
          </ThemedView>
        ))}
      </ThemedView>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    padding: 16,
    paddingTop: 56,
    gap: 16,
  },
  headerCard: {
    padding: 16,
    borderRadius: 12,
    gap: 10,
    borderWidth: 1,
    borderColor: '#2E5A6B',
  },
  subtitleText: {
    fontSize: 13,
    opacity: 0.8,
  },
  metaRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    flexWrap: 'wrap',
    gap: 8,
  },
  metaText: {
    fontSize: 12,
    fontWeight: '600',
  },
  refreshButton: {
    backgroundColor: '#0A7EA4',
    paddingVertical: 10,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: 4,
  },
  refreshButtonText: {
    color: '#FFFFFF',
    fontWeight: '700',
  },
  checklistCard: {
    padding: 14,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#3A3A3C',
    gap: 10,
  },
  checklistHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  checklistCount: {
    fontSize: 12,
    fontWeight: '700',
    color: '#0A7EA4',
  },
  pillsContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginTop: 2,
  },
  storePill: {
    paddingHorizontal: 12,
    paddingVertical: 7,
    borderRadius: 20,
    borderWidth: 1,
  },
  storePillSelected: {
    backgroundColor: '#0A7EA4',
    borderColor: '#0A7EA4',
  },
  storePillUnselected: {
    backgroundColor: 'transparent',
    borderColor: '#666',
  },
  storePillLocked: {
    opacity: 0.85,
  },
  storePillText: {
    fontSize: 12,
    fontWeight: '700',
  },
  storePillTextSelected: {
    color: '#FFFFFF',
  },
  storePillTextUnselected: {
    opacity: 0.75,
  },
  minStoreHint: {
    fontSize: 11,
    color: '#F59E0B',
    fontWeight: '600',
  },
  highlightCard: {
    padding: 16,
    borderRadius: 12,
    borderWidth: 2,
    borderColor: '#1B7F4C',
    gap: 8,
  },
  sectionTag: {
    fontSize: 11,
    fontWeight: '800',
    color: '#1B7F4C',
    letterSpacing: 0.8,
  },
  priceRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  storeInfo: {
    flex: 1,
    paddingRight: 8,
  },
  retailerSub: {
    fontSize: 12,
    opacity: 0.75,
  },
  priceHighlight: {
    color: '#1B7F4C',
  },
  splitCard: {
    padding: 16,
    borderRadius: 12,
    borderWidth: 2,
    borderColor: '#0A7EA4',
    gap: 10,
  },
  smartModeToggleRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: 12,
  },
  smartModeTitleGroup: {
    flex: 1,
    gap: 2,
  },
  splitBody: {
    gap: 10,
    paddingTop: 4,
  },
  splitHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: 8,
  },
  singleOptimalBadge: {
    backgroundColor: '#243B32',
    borderWidth: 1,
    borderColor: '#1B7F4C',
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderRadius: 8,
  },
  singleOptimalText: {
    fontSize: 12,
    color: '#A7F3D0',
    fontWeight: '600',
  },
  splitTag: {
    fontSize: 11,
    fontWeight: '800',
    color: '#0A7EA4',
    letterSpacing: 0.8,
  },
  savingsBadge: {
    backgroundColor: '#1B7F4C',
    color: '#FFFFFF',
    fontSize: 11,
    fontWeight: '700',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
  },
  splitPrice: {
    color: '#0A7EA4',
  },
  allocationBox: {
    padding: 10,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#3A3A3C',
    gap: 4,
  },
  allocationHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  lineItemText: {
    fontSize: 12,
    opacity: 0.85,
  },
  rankingsSection: {
    gap: 10,
  },
  storeRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 14,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#3A3A3C',
  },
  rankInfo: {
    flex: 1,
    paddingRight: 8,
  },
  storeTotalText: {
    fontSize: 16,
  },
});
