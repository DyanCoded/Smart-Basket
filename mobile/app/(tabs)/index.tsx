/**
 * KitchenSync Pantry Screen — Zero-Clutter Active Restock List (#26).
 *
 * - Active-Only Filtering: displays only `finished` and `low` items; marking an
 *   item `ok` removes it immediately while preserving household history in SQLite
 *   and PostgreSQL so searching in the top bar lets users re-flag it in one tap.
 * - View Mode Switcher: smooth toggle between `By Status` (Finished / Running Low)
 *   and `By Aisle` (only aisles with active items; tap an aisle to reveal items).
 * - Floating `Compare Prices (N)` CTA above the tab bar triggering a fresh
 *   `POST /api/v1/baskets/calculate` and opening the Basket tab.
 */

import { type Href, useRouter } from 'expo-router';
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import { IconSymbol } from '@/components/ui/IconSymbol';
import {
  getCardShadow,
  Radii,
  Spacing,
  Typography,
} from '@/constants/Theme';
import { useAuth } from '@/context/AuthContext';
import { useSyncStatus } from '@/context/SyncStatusContext';
import { useAppTheme } from '@/context/ThemeContext';
import {
  getActiveHomeId,
  searchCatalogProducts,
  setActiveHomeId,
} from '@/services/api';
import {
  recordOfflinePantryMutation,
  syncAndCalculateSmartBasket,
  syncOfflineQueueToServer,
  updatePantryItemStatusOfflineFirst,
} from '@/services/sync';
import { HouseholdRealtimeStream } from '@/services/websocket';
import {
  PantryItemResponse,
  PantryStatus,
  ProductResponse,
} from '@/types/api';

type PantryViewMode = 'status' | 'aisle';

const DEFAULT_HOME_ID = '00000000-0000-4000-8000-000000000001';

function generateUuidV4(): string {
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

function inferAisleLabel(item: PantryItemResponse): string {
  if (item.category_name && item.category_name.trim().length > 0) {
    return item.category_name.trim();
  }
  const title = (item.product_name ?? item.custom_name ?? '').toLowerCase();
  if (/(milk|egg|butter|yogurt|yoghurt|cheese|cream)/.test(title)) {
    return 'Dairy & Eggs';
  }
  if (/(bread|roll|wrap|croissant|bun|bagel)/.test(title)) {
    return 'Bakery';
  }
  if (/(apple|banana|potato|tomato|avocado|onion|spinach|veg|fruit)/.test(title)) {
    return 'Fresh Produce';
  }
  if (/(tea|coffee|juice|soda|water|cola|drink)/.test(title)) {
    return 'Beverages';
  }
  if (/(soap|wash|toilet|paper|detergent|dish|clean)/.test(title)) {
    return 'Household';
  }
  return 'Pantry & Staples';
}

function getItemTitle(item: PantryItemResponse): string {
  return item.product_name ?? item.custom_name ?? 'Pantry Staple';
}

function formatUnitSize(unitSize: string, unitType: string): string {
  const num = Number.parseFloat(unitSize);
  const cleanNum = Number.isFinite(num)
    ? Number.isInteger(num)
      ? String(num)
      : String(num)
    : unitSize.trim();
  const cleanUnit = unitType.trim();
  if (!cleanUnit || cleanUnit.toLowerCase() === 'unit') {
    return num === 1 ? '1 unit' : `${cleanNum}pk`;
  }
  return `${cleanNum}${cleanUnit}`;
}

function formatCatalogDropdownLabel(product: ProductResponse): string {
  const brand = product.brand?.trim() ?? '';
  let name = product.name.trim();
  if (brand && name.toLowerCase().startsWith(brand.toLowerCase())) {
    const stripped = name.slice(brand.length).replace(/^[\s·-]+/, '').trim();
    if (stripped.length > 0) {
      name = stripped;
    }
  }
  const sizeLabel = formatUnitSize(product.unit_size, product.unit_type);
  const nameLower = name.toLowerCase().replace(/\s+/g, '');
  const sizeLower = sizeLabel.toLowerCase().replace(/\s+/g, '');
  const parts: string[] = [];
  if (brand) {
    parts.push(brand);
  }
  parts.push(name);
  if (sizeLabel && !nameLower.includes(sizeLower)) {
    parts.push(sizeLabel);
  }
  return parts.join(' · ');
}

function inferProductCategoryBadge(product: ProductResponse): string {
  if (product.category?.name && product.category.name.trim().length > 0) {
    return product.category.name.trim();
  }
  const title = `${product.brand ?? ''} ${product.name}`.toLowerCase();
  if (/(milk|egg|butter|yogurt|yoghurt|cheese|cream)/.test(title)) {
    return 'Dairy & Eggs';
  }
  if (/(bread|roll|wrap|croissant|bun|bagel)/.test(title)) {
    return 'Bakery';
  }
  if (/(apple|banana|potato|tomato|avocado|onion|spinach|veg|fruit)/.test(title)) {
    return 'Fresh Produce';
  }
  if (/(tea|coffee|juice|soda|water|cola|drink)/.test(title)) {
    return 'Beverages';
  }
  if (/(soap|wash|toilet|paper|detergent|dish|clean)/.test(title)) {
    return 'Household';
  }
  return 'Pantry & Staples';
}

export default function PantryScreen() {
  const router = useRouter();
  const { colors, colorScheme } = useAppTheme();
  const { activeHomeId: authHomeId } = useAuth();
  const { setSyncState, setLatestComparison, selectedRetailerSlugs } =
    useSyncStatus();
  const homeId = authHomeId ?? getActiveHomeId() ?? DEFAULT_HOME_ID;

  const [items, setItems] = useState<PantryItemResponse[]>([]);
  const [viewMode, setViewMode] = useState<PantryViewMode>('status');
  const [expandedAisles, setExpandedAisles] = useState<Record<string, boolean>>({});
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [catalogResults, setCatalogResults] = useState<ProductResponse[]>([]);
  const [isSearchingCatalog, setIsSearchingCatalog] = useState<boolean>(false);
  const [catalogSearchError, setCatalogSearchError] = useState<string | null>(null);
  const [isComparing, setIsComparing] = useState<boolean>(false);
  const [recentRestocked, setRecentRestocked] = useState<{
    item: PantryItemResponse;
    previousStatus: PantryStatus;
  } | null>(null);
  const undoTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const cardShadow = getCardShadow(colorScheme);

  const loadAndSyncPantry = useCallback(async () => {
    setSyncState({ status: 'syncing' });
    setActiveHomeId(homeId);

    const summary = await syncOfflineQueueToServer(homeId);
    setItems(summary.items);
    setSyncState({
      status: summary.isOnline ? 'synced' : 'offline',
      pendingCount: summary.pendingCount,
      lastSyncedAt: summary.lastSyncedAt,
    });
  }, [homeId, setSyncState]);

  useEffect(() => {
    void loadAndSyncPantry();

    const stream = new HouseholdRealtimeStream(homeId, () => {
      void loadAndSyncPantry();
    });
    stream.connect();

    return () => {
      stream.disconnect();
      if (undoTimerRef.current) {
        clearTimeout(undoTimerRef.current);
      }
    };
  }, [homeId, loadAndSyncPantry]);

  // Active-only items (`finished` or `low`); `ok` items are hidden to eliminate clutter
  const activeItems = useMemo(
    () =>
      items.filter(
        (item) =>
          !item.is_deleted &&
          (item.status === 'finished' || item.status === 'low')
      ),
    [items]
  );

  const trimmedQuery = searchQuery.trim().toLowerCase();

  // Debounced (~250ms) live catalog autocomplete against GET /api/v1/products
  useEffect(() => {
    const clean = searchQuery.trim();
    if (clean.length < 2) {
      setCatalogResults([]);
      setIsSearchingCatalog(false);
      setCatalogSearchError(null);
      return;
    }

    const controller = new AbortController();
    setIsSearchingCatalog(true);
    setCatalogSearchError(null);

    const timer = setTimeout(() => {
      void searchCatalogProducts(clean, 15, controller.signal)
        .then((res) => {
          if (!controller.signal.aborted) {
            setCatalogResults(res.items);
            setIsSearchingCatalog(false);
          }
        })
        .catch((err: unknown) => {
          if (controller.signal.aborted) {
            return;
          }
          setCatalogResults([]);
          setIsSearchingCatalog(false);
          setCatalogSearchError(
            err instanceof Error ? err.message : 'Unable to search catalog'
          );
        });
    }, 250);

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [searchQuery]);

  // Hidden `ok` items matching search query so users can re-flag them in one tap
  const restockedSearchMatches = useMemo(() => {
    if (!trimmedQuery) {
      return [];
    }
    return items.filter(
      (item) =>
        !item.is_deleted &&
        item.status === 'ok' &&
        (getItemTitle(item).toLowerCase().includes(trimmedQuery) ||
          inferAisleLabel(item).toLowerCase().includes(trimmedQuery))
    );
  }, [items, trimmedQuery]);

  // Active items filtered by search query (if user is typing)
  const visibleActiveItems = useMemo(() => {
    if (!trimmedQuery) {
      return activeItems;
    }
    return activeItems.filter(
      (item) =>
        getItemTitle(item).toLowerCase().includes(trimmedQuery) ||
        inferAisleLabel(item).toLowerCase().includes(trimmedQuery)
    );
  }, [activeItems, trimmedQuery]);

  const finishedItems = useMemo(
    () => visibleActiveItems.filter((item) => item.status === 'finished'),
    [visibleActiveItems]
  );

  const lowItems = useMemo(
    () => visibleActiveItems.filter((item) => item.status === 'low'),
    [visibleActiveItems]
  );

  // Only aisles that contain >= 1 active (`finished` or `low`) item
  const activeAisles = useMemo(() => {
    const grouped = new Map<string, PantryItemResponse[]>();
    for (const item of visibleActiveItems) {
      const aisle = inferAisleLabel(item);
      const list = grouped.get(aisle) ?? [];
      list.push(item);
      grouped.set(aisle, list);
    }
    return Array.from(grouped.entries())
      .map(([aisle, aisleItems]) => {
        const sortedItems = [...aisleItems].sort((a, b) => {
          if (a.status === b.status) {
            return getItemTitle(a).localeCompare(getItemTitle(b));
          }
          return a.status === 'finished' ? -1 : 1;
        });
        return {
          aisle,
          items: sortedItems,
          finishedCount: sortedItems.filter((i) => i.status === 'finished').length,
          lowCount: sortedItems.filter((i) => i.status === 'low').length,
        };
      })
      .sort((a, b) => {
        if (b.finishedCount !== a.finishedCount) {
          return b.finishedCount - a.finishedCount;
        }
        return a.aisle.localeCompare(b.aisle);
      });
  }, [visibleActiveItems]);

  const handleStatusChange = async (
    item: PantryItemResponse,
    nextStatus: PantryStatus
  ) => {
    const previousStatus = item.status;

    // Optimistic update so marking `ok` removes the item from view immediately
    setItems((prev) =>
      prev.map((entry) =>
        entry.id === item.id ? { ...entry, status: nextStatus } : entry
      )
    );

    if (nextStatus === 'ok') {
      if (undoTimerRef.current) {
        clearTimeout(undoTimerRef.current);
      }
      setRecentRestocked({ item, previousStatus });
      undoTimerRef.current = setTimeout(() => {
        setRecentRestocked(null);
      }, 4500);
    }

    setSyncState({ status: 'syncing' });
    const summary = await updatePantryItemStatusOfflineFirst(
      homeId,
      item,
      nextStatus
    );
    setItems(summary.items);
    setSyncState({
      status: summary.isOnline ? 'synced' : 'offline',
      pendingCount: summary.pendingCount,
      lastSyncedAt: summary.lastSyncedAt,
    });
  };

  const handleUndoRestock = async () => {
    if (!recentRestocked) {
      return;
    }
    const { item, previousStatus } = recentRestocked;
    setRecentRestocked(null);
    await handleStatusChange(item, previousStatus);
  };

  const handleSelectCatalogProduct = async (
    product: ProductResponse,
    initialStatus: PantryStatus = 'low'
  ) => {
    setSearchQuery('');
    setCatalogResults([]);

    // If this exact catalog product is already in the household pantry, update it
    const existing = items.find(
      (entry) => !entry.is_deleted && entry.product_id === product.id
    );
    if (existing) {
      await handleStatusChange(existing, initialStatus);
      return;
    }

    const displayName = formatCatalogDropdownLabel(product);
    const newId = generateUuidV4();
    const nowIso = new Date().toISOString();

    const optimisticItem: PantryItemResponse = {
      id: newId,
      home_id: homeId,
      product_id: product.id,
      category_id: product.category_id,
      custom_name: displayName,
      barcode: product.barcode,
      quantity: initialStatus === 'finished' ? '0.00' : '1.00',
      unit_type: product.unit_type || 'unit',
      low_stock_threshold: '1.00',
      status: initialStatus,
      is_deleted: false,
      updated_at: nowIso,
      product_name: displayName,
      category_name: inferProductCategoryBadge(product),
    };

    setItems((prev) => [optimisticItem, ...prev]);
    setSyncState({ status: 'syncing' });

    const summary = await recordOfflinePantryMutation(homeId, {
      id: newId,
      product_id: product.id,
      category_id: product.category_id,
      custom_name: displayName,
      barcode: product.barcode,
      quantity: initialStatus === 'finished' ? '0.00' : '1.00',
      unit_type: product.unit_type || 'unit',
      low_stock_threshold: '1.00',
      status: initialStatus,
      updated_at: nowIso,
      is_deleted: false,
      note: `Added catalog product (${product.brand ?? 'brand'}) as ${initialStatus}`,
    });

    setItems(summary.items);
    setSyncState({
      status: summary.isOnline ? 'synced' : 'offline',
      pendingCount: summary.pendingCount,
      lastSyncedAt: summary.lastSyncedAt,
    });
  };

  const handleQuickAdd = async (initialStatus: PantryStatus = 'low') => {
    const cleanName = searchQuery.trim();
    if (!cleanName) {
      return;
    }

    const newId = generateUuidV4();
    setSearchQuery('');
    setCatalogResults([]);
    setSyncState({ status: 'syncing' });

    const summary = await recordOfflinePantryMutation(homeId, {
      id: newId,
      product_id: null,
      category_id: null,
      custom_name: cleanName,
      barcode: null,
      quantity: initialStatus === 'finished' ? '0.00' : '1.00',
      unit_type: 'unit',
      low_stock_threshold: '1.00',
      status: initialStatus,
      updated_at: new Date().toISOString(),
      is_deleted: false,
      note: `Quick-added as ${initialStatus} via mobile Pantry`,
    });

    setItems(summary.items);
    setSyncState({
      status: summary.isOnline ? 'synced' : 'offline',
      pendingCount: summary.pendingCount,
      lastSyncedAt: summary.lastSyncedAt,
    });
  };

  const handleToggleAisle = (aisleName: string) => {
    setExpandedAisles((prev) => ({
      ...prev,
      [aisleName]: !prev[aisleName],
    }));
  };

  const handleComparePrices = async () => {
    if (isComparing) {
      return;
    }
    setIsComparing(true);
    setSyncState({ status: 'syncing' });
    try {
      const comparisonResult = await syncAndCalculateSmartBasket(
        homeId,
        selectedRetailerSlugs
      );
      setLatestComparison(comparisonResult, selectedRetailerSlugs);
      setSyncState({
        status: comparisonResult.isLiveBackend ? 'synced' : 'offline',
      });
      router.push('/(tabs)/explore');
    } finally {
      setIsComparing(false);
    }
  };

  const renderActiveItemRow = (item: PantryItemResponse, showAisleSubtitle: boolean) => {
    const isFinished = item.status === 'finished';
    const dotColor = isFinished ? colors.statusFinished : colors.statusLow;
    const altStatus: PantryStatus = isFinished ? 'low' : 'finished';

    return (
      <View
        key={item.id}
        style={[
          styles.itemRow,
          {
            backgroundColor: colors.surfaceElevated,
            borderColor: colors.borderSubtle,
          },
        ]}>
        {/* One-tap Restocked (mark ok) check target */}
        <Pressable
          accessibilityRole="checkbox"
          accessibilityLabel={`Mark ${getItemTitle(item)} as restocked`}
          onPress={() => void handleStatusChange(item, 'ok')}
          style={({ pressed }) => [
            styles.checkCircle,
            {
              borderColor: colors.primary,
              backgroundColor: pressed ? colors.primaryMuted : 'transparent',
            },
          ]}>
          <IconSymbol name="checkmark" size={14} color={colors.primary} />
        </Pressable>

        {/* Item title + status dot + aisle metadata (tap catalog item for price sheet) */}
        <Pressable
          disabled={!item.product_id}
          accessibilityRole={item.product_id ? 'button' : undefined}
          accessibilityLabel={
            item.product_id
              ? `Compare cross-chain prices for ${getItemTitle(item)}`
              : undefined
          }
          onPress={() => {
            if (!item.product_id) {
              return;
            }
            const href = `/product/${encodeURIComponent(item.product_id)}?name=${encodeURIComponent(getItemTitle(item))}`;
            router.push(href as Href);
          }}
          style={({ pressed }) => [
            styles.itemInfo,
            { opacity: item.product_id && pressed ? 0.72 : 1 },
          ]}>
          <View style={styles.itemTitleLine}>
            <View style={[styles.statusDot, { backgroundColor: dotColor }]} />
            <Text
              numberOfLines={1}
              style={[Typography.bodySemiBold, { color: colors.text, flex: 1 }]}>
              {getItemTitle(item)}
            </Text>
            {item.product_id ? (
              <IconSymbol
                name="chevron.right"
                size={15}
                color={colors.textMuted}
              />
            ) : null}
          </View>
          <Text style={[Typography.caption, { color: colors.textMuted }]}>
            {showAisleSubtitle ? `${inferAisleLabel(item)} · ` : ''}
            {isFinished ? 'Out of stock' : `${item.quantity} ${item.unit_type} left`}
            {item.product_id ? ' · Tap for prices' : ''}
          </Text>
        </Pressable>

        {/* Quick toggle between Low <-> Finished */}
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={`Switch ${getItemTitle(item)} to ${altStatus}`}
          onPress={() => void handleStatusChange(item, altStatus)}
          style={({ pressed }) => [
            styles.statusPill,
            {
              backgroundColor: isFinished
                ? colors.statusFinishedBg
                : colors.statusLowBg,
              opacity: pressed ? 0.75 : 1,
            },
          ]}>
          <Text
            style={[
              Typography.badge,
              { color: isFinished ? colors.statusFinished : colors.statusLow },
            ]}>
            {isFinished ? 'Finished' : 'Low'}
          </Text>
        </Pressable>
      </View>
    );
  };

  return (
    <View style={[styles.screen, { backgroundColor: colors.background }]}>
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled">
        {/* Header Summary */}
        <View style={styles.headerRow}>
          <View style={styles.headerTitleGroup}>
            <Text style={[Typography.title, { color: colors.text }]}>
              Restock List
            </Text>
            <Text style={[Typography.caption, { color: colors.textSecondary }]}>
              {activeItems.length === 0
                ? 'Kitchen stocked · search below to flag items'
                : `${activeItems.length} active staple${activeItems.length === 1 ? '' : 's'} · tap ✓ when restocked`}
            </Text>
          </View>
          <View style={styles.counterPills}>
            {finishedItems.length > 0 ? (
              <View
                style={[
                  styles.miniCountBadge,
                  { backgroundColor: colors.statusFinishedBg },
                ]}>
                <View
                  style={[
                    styles.miniDot,
                    { backgroundColor: colors.statusFinished },
                  ]}
                />
                <Text
                  style={[
                    styles.miniCountText,
                    { color: colors.statusFinished },
                  ]}>
                  {finishedItems.length}
                </Text>
              </View>
            ) : null}
            {lowItems.length > 0 ? (
              <View
                style={[
                  styles.miniCountBadge,
                  { backgroundColor: colors.statusLowBg },
                ]}>
                <View
                  style={[styles.miniDot, { backgroundColor: colors.statusLow }]}
                />
                <Text style={[styles.miniCountText, { color: colors.statusLow }]}>
                  {lowItems.length}
                </Text>
              </View>
            ) : null}
          </View>
        </View>

        {/* Search Pantry & Quick-Flag / Quick-Add Bar */}
        <View
          style={[
            styles.searchBox,
            {
              backgroundColor: colors.surface,
              borderColor: colors.border,
            },
          ]}>
          <IconSymbol name="magnifyingglass" size={18} color={colors.textMuted} />
          <TextInput
            style={[styles.searchInput, { color: colors.text }]}
            placeholder="Search or add items..."
            placeholderTextColor={colors.textMuted}
            value={searchQuery}
            onChangeText={setSearchQuery}
            returnKeyType="done"
            onSubmitEditing={() => {
              if (
                restockedSearchMatches.length === 0 &&
                catalogResults.length === 0 &&
                searchQuery.trim()
              ) {
                void handleQuickAdd('low');
              }
            }}
          />
          {isSearchingCatalog ? (
            <ActivityIndicator size="small" color={colors.primary} />
          ) : null}
          {searchQuery.length > 0 ? (
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Clear search"
              onPress={() => {
                setSearchQuery('');
                setCatalogResults([]);
              }}
              hitSlop={8}>
              <IconSymbol name="xmark" size={16} color={colors.textMuted} />
            </Pressable>
          ) : null}
        </View>

        {/* Live Catalog Autocomplete + In-Pantry Re-Flag + Custom Fallback Dropdown */}
        {trimmedQuery.length > 0 ? (
          <View
            style={[
              styles.searchPanel,
              cardShadow,
              {
                backgroundColor: colors.surface,
                borderColor: colors.border,
              },
            ]}>
            {restockedSearchMatches.length > 0 ? (
              <View style={styles.searchSection}>
                <Text style={[Typography.badge, { color: colors.textMuted }]}>
                  IN PANTRY — TAP TO FLAG FOR RESTOCK
                </Text>
                {restockedSearchMatches.map((okItem) => (
                  <View
                    key={okItem.id}
                    style={[
                      styles.reFlagRow,
                      {
                        backgroundColor: colors.surfaceElevated,
                        borderColor: colors.borderSubtle,
                      },
                    ]}>
                    <View style={styles.itemInfo}>
                      <Text
                        numberOfLines={1}
                        style={[Typography.bodySemiBold, { color: colors.text }]}>
                        {getItemTitle(okItem)}
                      </Text>
                      <Text
                        style={[Typography.caption, { color: colors.textMuted }]}>
                        {inferAisleLabel(okItem)} · Currently in stock
                      </Text>
                    </View>
                    <View style={styles.reFlagActions}>
                      <Pressable
                        onPress={() => {
                          setSearchQuery('');
                          setCatalogResults([]);
                          void handleStatusChange(okItem, 'low');
                        }}
                        style={[
                          styles.flagChip,
                          { backgroundColor: colors.statusLowBg },
                        ]}>
                        <Text
                          style={[
                            Typography.badge,
                            { color: colors.statusLow },
                          ]}>
                          Low
                        </Text>
                      </Pressable>
                      <Pressable
                        onPress={() => {
                          setSearchQuery('');
                          setCatalogResults([]);
                          void handleStatusChange(okItem, 'finished');
                        }}
                        style={[
                          styles.flagChip,
                          { backgroundColor: colors.statusFinishedBg },
                        ]}>
                        <Text
                          style={[
                            Typography.badge,
                            { color: colors.statusFinished },
                          ]}>
                          Finished
                        </Text>
                      </Pressable>
                    </View>
                  </View>
                ))}
              </View>
            ) : null}

            {/* Live Catalog Matches (Brand · Name · Size + Category badge; zero prices) */}
            {trimmedQuery.length >= 2 ? (
              <View style={styles.searchSection}>
                <View style={styles.catalogSectionHeader}>
                  <Text style={[Typography.badge, { color: colors.textMuted }]}>
                    LIVE CATALOG MATCHES
                  </Text>
                  {isSearchingCatalog ? (
                    <Text style={[Typography.caption, { color: colors.textMuted }]}>
                      Searching…
                    </Text>
                  ) : null}
                </View>

                {catalogResults.length > 0 ? (
                  catalogResults.map((product) => {
                    const label = formatCatalogDropdownLabel(product);
                    const categoryBadge = inferProductCategoryBadge(product);
                    return (
                      <View
                        key={product.id}
                        style={[
                          styles.catalogRow,
                          {
                            backgroundColor: colors.surfaceElevated,
                            borderColor: colors.borderSubtle,
                          },
                        ]}>
                        <Pressable
                          accessibilityRole="button"
                          accessibilityLabel={`Add ${label} to pantry as low`}
                          onPress={() =>
                            void handleSelectCatalogProduct(product, 'low')
                          }
                          style={({ pressed }) => [
                            styles.catalogRowMain,
                            { opacity: pressed ? 0.72 : 1 },
                          ]}>
                          <Text
                            numberOfLines={2}
                            style={[
                              Typography.bodySemiBold,
                              { color: colors.text },
                            ]}>
                            {label}
                          </Text>
                          <View style={styles.catalogMetaRow}>
                            <View
                              style={[
                                styles.categoryBadgePill,
                                { backgroundColor: colors.surfaceMuted },
                              ]}>
                              <Text
                                style={[
                                  styles.categoryBadgeText,
                                  { color: colors.textSecondary },
                                ]}>
                                {categoryBadge}
                              </Text>
                            </View>
                          </View>
                        </Pressable>

                        <View style={styles.reFlagActions}>
                          <Pressable
                            accessibilityRole="button"
                            accessibilityLabel={`Add ${label} as low`}
                            onPress={() =>
                              void handleSelectCatalogProduct(product, 'low')
                            }
                            style={[
                              styles.flagChip,
                              { backgroundColor: colors.statusLowBg },
                            ]}>
                            <Text
                              style={[
                                Typography.badge,
                                { color: colors.statusLow },
                              ]}>
                              Low
                            </Text>
                          </Pressable>
                          <Pressable
                            accessibilityRole="button"
                            accessibilityLabel={`Add ${label} as finished`}
                            onPress={() =>
                              void handleSelectCatalogProduct(product, 'finished')
                            }
                            style={[
                              styles.flagChip,
                              { backgroundColor: colors.statusFinishedBg },
                            ]}>
                            <Text
                              style={[
                                Typography.badge,
                                { color: colors.statusFinished },
                              ]}>
                              Finished
                            </Text>
                          </Pressable>
                        </View>
                      </View>
                    );
                  })
                ) : !isSearchingCatalog ? (
                  <Text style={[Typography.caption, { color: colors.textMuted }]}>
                    {catalogSearchError
                      ? 'Offline — catalog search unavailable; add a custom item below.'
                      : 'No catalog brands matched — add it as a custom item below.'}
                  </Text>
                ) : null}
              </View>
            ) : null}

            {/* Secondary Custom Fallback Option */}
            <View
              style={[
                styles.customFallbackDivider,
                { borderTopColor: colors.borderSubtle },
              ]}>
              <View style={styles.quickAddRow}>
                <Pressable
                  onPress={() => void handleQuickAdd('low')}
                  style={[
                    styles.quickAddButton,
                    { backgroundColor: colors.primaryMuted },
                  ]}>
                  <IconSymbol name="plus" size={16} color={colors.primary} />
                  <Text
                    numberOfLines={1}
                    style={[styles.quickAddText, { color: colors.primary }]}>
                    Add &ldquo;{searchQuery.trim()}&rdquo; as custom item
                  </Text>
                </Pressable>
                <Pressable
                  onPress={() => void handleQuickAdd('finished')}
                  style={[
                    styles.quickAddFinishedBtn,
                    { backgroundColor: colors.statusFinishedBg },
                  ]}>
                  <Text
                    style={[Typography.badge, { color: colors.statusFinished }]}>
                    + Finished
                  </Text>
                </Pressable>
              </View>
            </View>
          </View>
        ) : null}

        {/* Undo Restocked Banner */}
        {recentRestocked ? (
          <View
            style={[
              styles.undoBanner,
              {
                backgroundColor: colors.surfaceElevated,
                borderColor: colors.primary,
              },
            ]}>
            <Text
              numberOfLines={1}
              style={[Typography.caption, { color: colors.text, flex: 1 }]}>
              Restocked {getItemTitle(recentRestocked.item)}
            </Text>
            <Pressable onPress={() => void handleUndoRestock()} hitSlop={8}>
              <Text style={[styles.undoLink, { color: colors.primary }]}>
                Undo
              </Text>
            </Pressable>
          </View>
        ) : null}

        {/* View Mode Switcher: By Status | By Aisle */}
        <View
          style={[
            styles.modeTrack,
            {
              backgroundColor: colors.surfaceMuted,
              borderColor: colors.borderSubtle,
            },
          ]}>
          {(
            [
              { key: 'status', label: 'By Status' },
              { key: 'aisle', label: 'By Aisle' },
            ] as const
          ).map((tab) => {
            const selected = viewMode === tab.key;
            return (
              <Pressable
                key={tab.key}
                accessibilityRole="tab"
                accessibilityState={{ selected }}
                onPress={() => setViewMode(tab.key)}
                style={[
                  styles.modePill,
                  selected && { backgroundColor: colors.primary },
                ]}>
                <Text
                  style={[
                    styles.modeLabel,
                    {
                      color: selected
                        ? colors.primaryText
                        : colors.textSecondary,
                    },
                  ]}>
                  {tab.label}
                </Text>
              </Pressable>
            );
          })}
        </View>

        {/* Active List Content */}
        {visibleActiveItems.length === 0 ? (
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
                { backgroundColor: colors.statusOkBg },
              ]}>
              <IconSymbol
                name="checkmark.circle.fill"
                size={28}
                color={colors.statusOk}
              />
            </View>
            <Text style={[Typography.subtitle, { color: colors.text }]}>
              {trimmedQuery ? 'No active matches' : 'Pantry is stocked up'}
            </Text>
            <Text
              style={[
                Typography.body,
                styles.emptySubtitle,
                { color: colors.textSecondary },
              ]}>
              {trimmedQuery
                ? 'Use the quick-flag or + Add buttons above to add this staple to your restock list.'
                : 'All items are in stock. Search any household staple above whenever something runs low or finishes.'}
            </Text>
          </View>
        ) : viewMode === 'status' ? (
          <View style={styles.sectionsStack}>
            {/* Finished Group Card */}
            {finishedItems.length > 0 ? (
              <View
                style={[
                  styles.groupCard,
                  cardShadow,
                  {
                    backgroundColor: colors.surface,
                    borderColor: colors.border,
                  },
                ]}>
                <View style={styles.groupHeader}>
                  <View style={styles.groupTitleRow}>
                    <View
                      style={[
                        styles.groupDot,
                        { backgroundColor: colors.statusFinished },
                      ]}
                    />
                    <Text style={[Typography.cardTitle, { color: colors.text }]}>
                      Finished
                    </Text>
                  </View>
                  <View
                    style={[
                      styles.groupCountPill,
                      { backgroundColor: colors.statusFinishedBg },
                    ]}>
                    <Text
                      style={[
                        Typography.badge,
                        { color: colors.statusFinished },
                      ]}>
                      {finishedItems.length}
                    </Text>
                  </View>
                </View>

                <View style={styles.groupItems}>
                  {finishedItems.map((item) => renderActiveItemRow(item, true))}
                </View>
              </View>
            ) : null}

            {/* Running Low Group Card */}
            {lowItems.length > 0 ? (
              <View
                style={[
                  styles.groupCard,
                  cardShadow,
                  {
                    backgroundColor: colors.surface,
                    borderColor: colors.border,
                  },
                ]}>
                <View style={styles.groupHeader}>
                  <View style={styles.groupTitleRow}>
                    <View
                      style={[
                        styles.groupDot,
                        { backgroundColor: colors.statusLow },
                      ]}
                    />
                    <Text style={[Typography.cardTitle, { color: colors.text }]}>
                      Running Low
                    </Text>
                  </View>
                  <View
                    style={[
                      styles.groupCountPill,
                      { backgroundColor: colors.statusLowBg },
                    ]}>
                    <Text
                      style={[Typography.badge, { color: colors.statusLow }]}>
                      {lowItems.length}
                    </Text>
                  </View>
                </View>

                <View style={styles.groupItems}>
                  {lowItems.map((item) => renderActiveItemRow(item, true))}
                </View>
              </View>
            ) : null}
          </View>
        ) : (
          /* By Aisle View: Only aisles with active items; tap an aisle to reveal items */
          <View style={styles.sectionsStack}>
            {activeAisles.map(({ aisle, items: aisleItems, finishedCount, lowCount }) => {
              const isExpanded = Boolean(expandedAisles[aisle]);
              return (
                <View
                  key={aisle}
                  style={[
                    styles.groupCard,
                    cardShadow,
                    {
                      backgroundColor: colors.surface,
                      borderColor: isExpanded ? colors.primary : colors.border,
                    },
                  ]}>
                  <Pressable
                    accessibilityRole="button"
                    accessibilityState={{ expanded: isExpanded }}
                    onPress={() => handleToggleAisle(aisle)}
                    style={styles.aisleHeaderButton}>
                    <View style={styles.aisleTitleBlock}>
                      <Text
                        style={[Typography.cardTitle, { color: colors.text }]}>
                        {aisle}
                      </Text>
                      <View style={styles.aisleDotSummary}>
                        {aisleItems.map((entry) => (
                          <View
                            key={entry.id}
                            style={[
                              styles.aisleMiniDot,
                              {
                                backgroundColor:
                                  entry.status === 'finished'
                                    ? colors.statusFinished
                                    : colors.statusLow,
                              },
                            ]}
                          />
                        ))}
                        <Text
                          style={[
                            Typography.caption,
                            { color: colors.textMuted, marginLeft: 4 },
                          ]}>
                          {[
                            finishedCount > 0 ? `${finishedCount} finished` : null,
                            lowCount > 0 ? `${lowCount} low` : null,
                          ]
                            .filter(Boolean)
                            .join(' · ')}
                        </Text>
                      </View>
                    </View>

                    <View style={styles.aisleRightGroup}>
                      <View
                        style={[
                          styles.groupCountPill,
                          { backgroundColor: colors.surfaceElevated },
                        ]}>
                        <Text
                          style={[Typography.badge, { color: colors.text }]}>
                          {aisleItems.length}
                        </Text>
                      </View>
                      <IconSymbol
                        name={isExpanded ? 'chevron.up' : 'chevron.down'}
                        size={20}
                        color={colors.textSecondary}
                      />
                    </View>
                  </Pressable>

                  {isExpanded ? (
                    <View style={styles.groupItems}>
                      {aisleItems.map((item) => renderActiveItemRow(item, false))}
                    </View>
                  ) : null}
                </View>
              );
            })}
          </View>
        )}
      </ScrollView>

      {/* Floating Compare Prices (N) CTA Button */}
      <View pointerEvents="box-none" style={styles.floatingFooter}>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={`Compare Prices for ${activeItems.length} active pantry items`}
          onPress={() => void handleComparePrices()}
          disabled={isComparing}
          style={({ pressed }) => [
            styles.compareCta,
            cardShadow,
            {
              backgroundColor: pressed ? colors.primaryPressed : colors.primary,
              opacity: isComparing ? 0.85 : 1,
            },
          ]}>
          {isComparing ? (
            <ActivityIndicator size="small" color={colors.primaryText} />
          ) : (
            <IconSymbol
              name="basket.fill"
              size={20}
              color={colors.primaryText}
            />
          )}
          <Text style={[styles.compareCtaText, { color: colors.primaryText }]}>
            {isComparing
              ? 'Comparing 5 National Chains…'
              : `Compare Prices (${activeItems.length})`}
          </Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {
    flex: 1,
  },
  scrollContent: {
    padding: Spacing.lg,
    paddingBottom: 108,
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
  counterPills: {
    flexDirection: 'row',
    gap: 6,
  },
  miniCountBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    paddingHorizontal: 9,
    paddingVertical: 5,
    borderRadius: Radii.pill,
  },
  miniDot: {
    width: 7,
    height: 7,
    borderRadius: Radii.pill,
  },
  miniCountText: {
    fontSize: 12,
    fontWeight: '800',
  },
  searchBox: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
    paddingHorizontal: Spacing.md,
    paddingVertical: 10,
    borderRadius: Radii.lg,
    borderWidth: 1,
  },
  searchInput: {
    flex: 1,
    fontSize: 15,
    paddingVertical: 2,
  },
  searchPanel: {
    borderRadius: Radii.lg,
    padding: Spacing.md,
    borderWidth: 1,
    gap: Spacing.md,
  },
  searchSection: {
    gap: Spacing.sm,
  },
  catalogSectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  catalogRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Spacing.sm,
    paddingHorizontal: Spacing.sm + 4,
    paddingVertical: 10,
    borderRadius: Radii.md,
    borderWidth: 1,
  },
  catalogRowMain: {
    flex: 1,
    gap: 5,
  },
  catalogMetaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: 6,
  },
  categoryBadgePill: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: Radii.pill,
  },
  categoryBadgeText: {
    fontSize: 11,
    fontWeight: '700',
  },
  customFallbackDivider: {
    borderTopWidth: 1,
    paddingTop: Spacing.sm,
  },
  reFlagRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Spacing.sm,
    padding: Spacing.sm + 2,
    borderRadius: Radii.md,
    borderWidth: 1,
  },
  reFlagActions: {
    flexDirection: 'row',
    gap: 6,
  },
  flagChip: {
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: Radii.pill,
  },
  quickAddRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
  },
  quickAddButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    paddingVertical: 10,
    paddingHorizontal: Spacing.md,
    borderRadius: Radii.md,
  },
  quickAddText: {
    fontSize: 13,
    fontWeight: '700',
    flexShrink: 1,
  },
  quickAddFinishedBtn: {
    paddingVertical: 10,
    paddingHorizontal: 12,
    borderRadius: Radii.md,
  },
  undoBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Spacing.md,
    paddingHorizontal: Spacing.md,
    paddingVertical: 10,
    borderRadius: Radii.md,
    borderWidth: 1,
  },
  undoLink: {
    fontSize: 13,
    fontWeight: '800',
  },
  modeTrack: {
    flexDirection: 'row',
    padding: 4,
    borderRadius: Radii.md,
    borderWidth: 1,
    gap: 4,
  },
  modePill: {
    flex: 1,
    paddingVertical: 9,
    borderRadius: Radii.sm,
    alignItems: 'center',
  },
  modeLabel: {
    fontSize: 14,
    fontWeight: '700',
  },
  sectionsStack: {
    gap: Spacing.md,
  },
  groupCard: {
    borderRadius: Radii.lg,
    padding: Spacing.md,
    borderWidth: 1,
    gap: Spacing.sm + 2,
  },
  groupHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 2,
  },
  groupTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
  },
  groupDot: {
    width: 10,
    height: 10,
    borderRadius: Radii.pill,
  },
  groupCountPill: {
    paddingHorizontal: 9,
    paddingVertical: 3,
    borderRadius: Radii.pill,
  },
  groupItems: {
    gap: Spacing.sm,
  },
  itemRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm + 2,
    paddingHorizontal: Spacing.md,
    paddingVertical: 12,
    borderRadius: Radii.md,
    borderWidth: 1,
  },
  checkCircle: {
    width: 26,
    height: 26,
    borderRadius: Radii.pill,
    borderWidth: 2,
    alignItems: 'center',
    justifyContent: 'center',
  },
  itemInfo: {
    flex: 1,
    gap: 2,
  },
  itemTitleLine: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 7,
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: Radii.pill,
  },
  statusPill: {
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: Radii.pill,
  },
  aisleHeaderButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Spacing.sm,
    paddingVertical: 2,
  },
  aisleTitleBlock: {
    flex: 1,
    gap: 4,
  },
  aisleDotSummary: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    flexWrap: 'wrap',
  },
  aisleMiniDot: {
    width: 7,
    height: 7,
    borderRadius: Radii.pill,
  },
  aisleRightGroup: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.xs + 2,
  },
  emptyCard: {
    borderRadius: Radii.xl,
    padding: Spacing.xxl,
    borderWidth: 1,
    alignItems: 'center',
    gap: Spacing.sm,
  },
  emptyIconCircle: {
    width: 52,
    height: 52,
    borderRadius: Radii.pill,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: Spacing.xs,
  },
  emptySubtitle: {
    textAlign: 'center',
  },
  floatingFooter: {
    position: 'absolute',
    left: Spacing.lg,
    right: Spacing.lg,
    bottom: Spacing.md,
  },
  compareCta: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.sm,
    paddingVertical: 15,
    paddingHorizontal: Spacing.xl,
    borderRadius: Radii.pill,
  },
  compareCtaText: {
    fontSize: 16,
    fontWeight: '800',
    letterSpacing: -0.2,
  },
});
