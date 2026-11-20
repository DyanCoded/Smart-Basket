import React, { useCallback, useEffect, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, TextInput, View } from 'react-native';

import { ThemedText } from '@/components/ThemedText';
import { ThemedView } from '@/components/ThemedView';
import {
  enqueuePendingSync,
  getLocalPantryItems,
  upsertLocalPantryItem,
} from '@/db/sqlite';
import { getActiveHomeId, setActiveHomeId } from '@/services/api';
import {
  recordOfflinePantryMutation,
  SEED_CATALOG_PRODUCTS,
  syncOfflineQueueToServer,
  updatePantryItemStatusOfflineFirst,
} from '@/services/sync';
import { HouseholdRealtimeStream } from '@/services/websocket';
import { PantryItemResponse, PantryStatus } from '@/types/api';

const DEFAULT_HOME_ID = '00000000-0000-4000-8000-000000000001';

function generateUuidV4(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

const INITIAL_PANTRY_FIXTURES: PantryItemResponse[] = [
  {
    id: '10000000-0000-4000-8000-000000000001',
    home_id: DEFAULT_HOME_ID,
    product_id: SEED_CATALOG_PRODUCTS.MILK_2L.id,
    category_id: null,
    custom_name: SEED_CATALOG_PRODUCTS.MILK_2L.name,
    barcode: '6001299011011',
    quantity: '1.00',
    unit_type: SEED_CATALOG_PRODUCTS.MILK_2L.unit_type,
    low_stock_threshold: '2.00',
    status: 'low',
    is_deleted: false,
    updated_at: new Date().toISOString(),
    product_name: SEED_CATALOG_PRODUCTS.MILK_2L.name,
    category_name: 'Dairy & Eggs',
  },
  {
    id: '10000000-0000-4000-8000-000000000002',
    home_id: DEFAULT_HOME_ID,
    product_id: SEED_CATALOG_PRODUCTS.WHITE_BREAD_700G.id,
    category_id: null,
    custom_name: SEED_CATALOG_PRODUCTS.WHITE_BREAD_700G.name,
    barcode: '6001299011059',
    quantity: '0.00',
    unit_type: SEED_CATALOG_PRODUCTS.WHITE_BREAD_700G.unit_type,
    low_stock_threshold: '1.00',
    status: 'finished',
    is_deleted: false,
    updated_at: new Date().toISOString(),
    product_name: SEED_CATALOG_PRODUCTS.WHITE_BREAD_700G.name,
    category_name: 'Bakery',
  },
  {
    id: '10000000-0000-4000-8000-000000000003',
    home_id: DEFAULT_HOME_ID,
    product_id: SEED_CATALOG_PRODUCTS.LARGE_EGGS_18PK.id,
    category_id: null,
    custom_name: SEED_CATALOG_PRODUCTS.LARGE_EGGS_18PK.name,
    barcode: '6001299011028',
    quantity: '2.00',
    unit_type: SEED_CATALOG_PRODUCTS.LARGE_EGGS_18PK.unit_type,
    low_stock_threshold: '1.00',
    status: 'ok',
    is_deleted: false,
    updated_at: new Date().toISOString(),
    product_name: SEED_CATALOG_PRODUCTS.LARGE_EGGS_18PK.name,
    category_name: 'Dairy & Eggs',
  },
];

export default function PantryScreen() {
  const homeId = getActiveHomeId() ?? DEFAULT_HOME_ID;
  const [items, setItems] = useState<PantryItemResponse[]>([]);
  const [isOnline, setIsOnline] = useState<boolean>(false);
  const [pendingCount, setPendingCount] = useState<number>(0);
  const [lastSyncedAt, setLastSyncedAt] = useState<string | null>(null);
  const [newItemName, setNewItemName] = useState<string>('');
  const [isSyncing, setIsSyncing] = useState<boolean>(false);

  const loadAndSyncPantry = useCallback(async () => {
    setIsSyncing(true);
    setActiveHomeId(homeId);

    const existing = await getLocalPantryItems(homeId);
    if (existing.length === 0) {
      for (const seedItem of INITIAL_PANTRY_FIXTURES) {
        await upsertLocalPantryItem(seedItem);
        await enqueuePendingSync(homeId, {
          id: seedItem.id,
          product_id: seedItem.product_id,
          category_id: seedItem.category_id,
          custom_name: seedItem.custom_name,
          barcode: seedItem.barcode,
          quantity: seedItem.quantity,
          unit_type: seedItem.unit_type,
          low_stock_threshold: seedItem.low_stock_threshold,
          status: seedItem.status,
          updated_at: seedItem.updated_at,
          is_deleted: false,
          note: 'Initial household pantry seed',
        });
      }
    }

    const summary = await syncOfflineQueueToServer(homeId);
    setItems(summary.items);
    setIsOnline(summary.isOnline);
    setPendingCount(summary.pendingCount);
    setLastSyncedAt(summary.lastSyncedAt);
    setIsSyncing(false);
  }, [homeId]);

  useEffect(() => {
    void loadAndSyncPantry();

    const stream = new HouseholdRealtimeStream(homeId, () => {
      void loadAndSyncPantry();
    });
    stream.connect();

    return () => {
      stream.disconnect();
    };
  }, [homeId, loadAndSyncPantry]);

  const handleStatusChange = async (
    item: PantryItemResponse,
    nextStatus: PantryStatus
  ) => {
    setIsSyncing(true);
    const summary = await updatePantryItemStatusOfflineFirst(
      homeId,
      item,
      nextStatus
    );
    setItems(summary.items);
    setIsOnline(summary.isOnline);
    setPendingCount(summary.pendingCount);
    setLastSyncedAt(summary.lastSyncedAt);
    setIsSyncing(false);
  };

  const handleAddItem = async () => {
    const cleanName = newItemName.trim();
    if (!cleanName) {
      return;
    }

    setIsSyncing(true);
    const newId = generateUuidV4();
    const summary = await recordOfflinePantryMutation(homeId, {
      id: newId,
      product_id: null,
      category_id: null,
      custom_name: cleanName,
      barcode: null,
      quantity: '1.00',
      unit_type: 'unit',
      low_stock_threshold: '1.00',
      status: 'low',
      updated_at: new Date().toISOString(),
      is_deleted: false,
      note: 'Added via mobile pantry quick-add',
    });

    setNewItemName('');
    setItems(summary.items);
    setIsOnline(summary.isOnline);
    setPendingCount(summary.pendingCount);
    setLastSyncedAt(summary.lastSyncedAt);
    setIsSyncing(false);
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <ThemedView style={styles.headerCard}>
        <ThemedText type="title">KitchenSync Pantry</ThemedText>
        <ThemedText style={styles.subtitleText}>
          Offline-first SQLite inventory bridged to SmartBasket price comparison
        </ThemedText>

        <View style={styles.syncStatusRow}>
          <View
            style={[
              styles.statusBadge,
              isOnline ? styles.onlineBadge : styles.offlineBadge,
            ]}>
            <ThemedText style={styles.badgeText}>
              {isOnline ? 'ONLINE (Live FastAPI)' : 'OFFLINE (SQLite Queue)'}
            </ThemedText>
          </View>
          <ThemedText style={styles.queueText}>
            Pending Sync: {pendingCount}
          </ThemedText>
        </View>

        {lastSyncedAt && (
          <ThemedText style={styles.timestampText}>
            Last Synced: {new Date(lastSyncedAt).toLocaleTimeString()}
          </ThemedText>
        )}

        <Pressable
          style={styles.syncButton}
          onPress={() => void loadAndSyncPantry()}
          disabled={isSyncing}>
          <ThemedText style={styles.syncButtonText}>
            {isSyncing ? 'Syncing Delta Queue...' : 'Sync Now (/pantry/sync)'}
          </ThemedText>
        </Pressable>
      </ThemedView>

      <ThemedView style={styles.addCard}>
        <ThemedText type="subtitle">Quick-Add Pantry Staple</ThemedText>
        <View style={styles.addRow}>
          <TextInput
            style={styles.input}
            placeholder="e.g. Rooibos Tea 80pk..."
            placeholderTextColor="#888"
            value={newItemName}
            onChangeText={setNewItemName}
          />
          <Pressable style={styles.addButton} onPress={() => void handleAddItem()}>
            <ThemedText style={styles.addButtonText}>+ Add</ThemedText>
          </Pressable>
        </View>
      </ThemedView>

      <ThemedView style={styles.listSection}>
        <ThemedText type="subtitle">
          Household Inventory ({items.length})
        </ThemedText>
        {items.map((item) => {
          const displayTitle = item.product_name ?? item.custom_name ?? 'Pantry Item';
          return (
            <ThemedView key={item.id} style={styles.itemCard}>
              <View style={styles.itemHeader}>
                <View style={styles.itemTitleGroup}>
                  <ThemedText type="defaultSemiBold">{displayTitle}</ThemedText>
                  <ThemedText style={styles.itemMeta}>
                    Qty: {item.quantity} {item.unit_type} · Threshold:{' '}
                    {item.low_stock_threshold}
                    {item.product_id ? ' · Linked to Catalog' : ' · Custom Item'}
                  </ThemedText>
                </View>
                <View
                  style={[
                    styles.stockBadge,
                    item.status === 'ok'
                      ? styles.stockOk
                      : item.status === 'low'
                        ? styles.stockLow
                        : styles.stockFinished,
                  ]}>
                  <ThemedText style={styles.stockBadgeText}>
                    {item.status.toUpperCase()}
                  </ThemedText>
                </View>
              </View>

              <View style={styles.actionRow}>
                {(['ok', 'low', 'finished'] as PantryStatus[]).map((statusOption) => (
                  <Pressable
                    key={statusOption}
                    style={[
                      styles.actionButton,
                      item.status === statusOption && styles.actionButtonActive,
                    ]}
                    onPress={() => void handleStatusChange(item, statusOption)}>
                    <ThemedText style={styles.actionButtonText}>
                      Mark {statusOption.toUpperCase()}
                    </ThemedText>
                  </Pressable>
                ))}
              </View>
            </ThemedView>
          );
        })}
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
  syncStatusRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginTop: 4,
  },
  statusBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 6,
  },
  onlineBadge: {
    backgroundColor: '#1B7F4C',
  },
  offlineBadge: {
    backgroundColor: '#9B5B00',
  },
  badgeText: {
    color: '#FFFFFF',
    fontSize: 12,
    fontWeight: '700',
  },
  queueText: {
    fontSize: 13,
    fontWeight: '600',
  },
  timestampText: {
    fontSize: 12,
    opacity: 0.7,
  },
  syncButton: {
    backgroundColor: '#0A7EA4',
    paddingVertical: 10,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: 4,
  },
  syncButtonText: {
    color: '#FFFFFF',
    fontWeight: '700',
  },
  addCard: {
    padding: 14,
    borderRadius: 12,
    gap: 10,
    borderWidth: 1,
    borderColor: '#3A3A3C',
  },
  addRow: {
    flexDirection: 'row',
    gap: 8,
  },
  input: {
    flex: 1,
    borderWidth: 1,
    borderColor: '#666',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 8,
    color: '#ECEDEE',
  },
  addButton: {
    backgroundColor: '#1B7F4C',
    paddingHorizontal: 16,
    justifyContent: 'center',
    borderRadius: 8,
  },
  addButtonText: {
    color: '#FFFFFF',
    fontWeight: '700',
  },
  listSection: {
    gap: 12,
  },
  itemCard: {
    padding: 14,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#3A3A3C',
    gap: 10,
  },
  itemHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  itemTitleGroup: {
    flex: 1,
    paddingRight: 8,
  },
  itemMeta: {
    fontSize: 12,
    opacity: 0.75,
    marginTop: 2,
  },
  stockBadge: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
  },
  stockOk: {
    backgroundColor: '#1B7F4C',
  },
  stockLow: {
    backgroundColor: '#C97A00',
  },
  stockFinished: {
    backgroundColor: '#B3261E',
  },
  stockBadgeText: {
    color: '#FFFFFF',
    fontSize: 11,
    fontWeight: '700',
  },
  actionRow: {
    flexDirection: 'row',
    gap: 8,
  },
  actionButton: {
    flex: 1,
    paddingVertical: 6,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#0A7EA4',
    alignItems: 'center',
  },
  actionButtonActive: {
    backgroundColor: '#0A7EA4',
  },
  actionButtonText: {
    fontSize: 11,
    fontWeight: '600',
  },
});
