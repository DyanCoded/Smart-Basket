import React, { useCallback, useEffect, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, View } from 'react-native';

import { ThemedText } from '@/components/ThemedText';
import { ThemedView } from '@/components/ThemedView';
import { getActiveHomeId } from '@/services/api';
import {
  HouseholdBasketComparisonResult,
  syncAndCalculateSmartBasket,
} from '@/services/sync';

const DEFAULT_HOME_ID = '00000000-0000-4000-8000-000000000001';

export default function SmartBasketScreen() {
  const homeId = getActiveHomeId() ?? DEFAULT_HOME_ID;
  const [comparison, setComparison] =
    useState<HouseholdBasketComparisonResult | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);

  const refreshComparison = useCallback(async () => {
    setIsLoading(true);
    const result = await syncAndCalculateSmartBasket(homeId);
    setComparison(result);
    setIsLoading(false);
  }, [homeId]);

  useEffect(() => {
    void refreshComparison();
  }, [refreshComparison]);

  const calc = comparison?.calculation;
  const cheapestSingle = calc?.cheapest_single_store;
  const optimalSplit = calc?.optimal_split;
  const rankedStores = calc?.ranked_stores ?? [];

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <ThemedView style={styles.headerCard}>
        <ThemedText type="title">SmartBasket Optimizer</ThemedText>
        <ThemedText style={styles.subtitleText}>
          Multi-store price comparison fed by low & finished household pantry staples
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
          onPress={() => void refreshComparison()}
          disabled={isLoading}>
          <ThemedText style={styles.refreshButtonText}>
            {isLoading
              ? 'Calculating Best Prices...'
              : 'Recalculate Multi-Store Totals'}
          </ThemedText>
        </Pressable>
      </ThemedView>

      {cheapestSingle && (
        <ThemedView style={styles.highlightCard}>
          <ThemedText style={styles.sectionTag}>
            CHEAPEST SINGLE STORE
          </ThemedText>
          <View style={styles.priceRow}>
            <View style={styles.storeInfo}>
              <ThemedText type="subtitle">{cheapestSingle.store_name}</ThemedText>
              <ThemedText style={styles.retailerSub}>
                {cheapestSingle.retailer_name} ·{' '}
                {cheapestSingle.items_available_count}/
                {cheapestSingle.total_items_count} items available
              </ThemedText>
            </View>
            <ThemedText type="title" style={styles.priceHighlight}>
              R{cheapestSingle.total_price}
            </ThemedText>
          </View>
        </ThemedView>
      )}

      {optimalSplit && optimalSplit.cheaper_than_single_store && (
        <ThemedView style={styles.splitCard}>
          <View style={styles.splitHeader}>
            <ThemedText style={styles.splitTag}>
              SMART MODE: 2-STORE SPLIT
            </ThemedText>
            <ThemedText style={styles.savingsBadge}>
              Save R{optimalSplit.savings_amount} ({optimalSplit.savings_percentage}%)
            </ThemedText>
          </View>

          <View style={styles.priceRow}>
            <ThemedText type="subtitle">Optimal Split Total</ThemedText>
            <ThemedText type="title" style={styles.splitPrice}>
              R{optimalSplit.total_price}
            </ThemedText>
          </View>

          {optimalSplit.stores.map((allocation) => (
            <View key={allocation.store_id} style={styles.allocationBox}>
              <View style={styles.allocationHeader}>
                <ThemedText type="defaultSemiBold">
                  {allocation.store_name}
                </ThemedText>
                <ThemedText type="defaultSemiBold">
                  Subtotal: R{allocation.subtotal}
                </ThemedText>
              </View>
              {allocation.items.map((item) => (
                <ThemedText key={item.product_id} style={styles.lineItemText}>
                  • {item.product_name} ({item.quantity}x @ R{item.unit_price}) = R
                  {item.subtotal}
                  {item.is_promotional ? ' [PROMO]' : ''}
                </ThemedText>
              ))}
            </View>
          ))}
        </ThemedView>
      )}

      <ThemedView style={styles.rankingsSection}>
        <ThemedText type="subtitle">
          All Monitored Retailers ({rankedStores.length})
        </ThemedText>
        {rankedStores.map((store, index) => (
          <ThemedView key={store.store_id} style={styles.storeRow}>
            <View style={styles.rankInfo}>
              <ThemedText type="defaultSemiBold">
                #{index + 1} {store.store_name}
              </ThemedText>
              <ThemedText style={styles.retailerSub}>
                {store.retailer_name} ·{' '}
                {store.is_complete_match ? 'Complete Match' : 'Partial Match'} (
                {store.items_available_count}/{store.total_items_count})
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
  splitHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
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
