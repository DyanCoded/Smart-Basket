/**
 * Offline-to-online SQLite delta synchronization engine and SmartBasket
 * replenishment bridge.
 *
 * Queues local pantry mutations in SQLite (`pending_sync`), synchronizes
 * against `POST /api/v1/homes/{home_id}/pantry/sync`, and evaluates live
 * multi-store basket totals via `POST /api/v1/baskets/calculate`.
 */

import {
  applyServerDeltasToLocalDb,
  clearPendingSyncMutations,
  enqueuePendingSync,
  getLastSyncedAt,
  getLocalPantryItems,
  getPendingSyncMutations,
} from '@/db/sqlite';
import {
  calculateMultiStoreBasket,
  ensureAuthenticatedHousehold,
  fetchHouseholdBasket,
  postPantryDeltaSync,
} from '@/services/api';
import {
  BasketCalculationResponse,
  BasketItemRequest,
  HouseholdBasketResponse,
  PantryItemResponse,
  PantryStatus,
  PantrySyncMutation,
  PantrySyncResponse,
} from '@/types/api';

export interface NationalRetailerOption {
  slug: string;
  name: string;
  store_id: string;
}

export const NATIONAL_RETAILER_CHAINS: NationalRetailerOption[] = [
  {
    slug: 'shoprite',
    name: 'Shoprite',
    store_id: 'd1b6fc61-ff2b-5935-8d92-9eec487eeaae',
  },
  {
    slug: 'checkers',
    name: 'Checkers',
    store_id: '26f7a89e-0e58-56e3-a225-8c7310382985',
  },
  {
    slug: 'pick-n-pay',
    name: 'Pick n Pay',
    store_id: 'cd86c9b4-176c-551e-aebc-b91bfdce86c1',
  },
  {
    slug: 'spar',
    name: 'SPAR',
    store_id: 'c9753b0f-5341-5001-a2dc-3996ff85a7bc',
  },
  {
    slug: 'woolworths-food',
    name: 'Woolworths Food',
    store_id: '30c7639b-d34c-597b-9399-68e3ff9de7a7',
  },
];

// Deterministic UUIDv5 catalog product IDs from SmartBasket seed fixtures
export const SEED_CATALOG_PRODUCTS = {
  MILK_2L: {
    id: '6e2941e3-033d-5768-8143-5e7ebc24b874',
    name: 'Full Cream Fresh Milk 2L',
    unit_type: 'L',
  },
  WHITE_BREAD_700G: {
    id: 'ab9928f5-221a-5546-8b6c-c4ec04fbe933',
    name: 'Superior Sliced White Bread 700g',
    unit_type: 'loaf',
  },
  LARGE_EGGS_18PK: {
    id: '4ca9f9c4-dea2-5f16-8ffb-4ec70ea08382',
    name: 'Large Eggs 18pk',
    unit_type: 'pack',
  },
};

export interface SyncStatusSummary {
  isOnline: boolean;
  pendingCount: number;
  lastSyncedAt: string | null;
  appliedCount: number;
  items: PantryItemResponse[];
}

export async function recordOfflinePantryMutation(
  homeId: string,
  mutation: PantrySyncMutation
): Promise<SyncStatusSummary> {
  await enqueuePendingSync(homeId, mutation);
  return syncOfflineQueueToServer(homeId);
}

export async function updatePantryItemStatusOfflineFirst(
  homeId: string,
  item: PantryItemResponse,
  newStatus: PantryStatus,
  newQuantity?: string
): Promise<SyncStatusSummary> {
  const updatedQuantity =
    newQuantity ??
    (newStatus === 'finished' ? '0.00' : newStatus === 'low' ? '1.00' : item.quantity);

  const mutation: PantrySyncMutation = {
    id: item.id,
    product_id: item.product_id,
    category_id: item.category_id,
    custom_name: item.custom_name ?? item.product_name,
    barcode: item.barcode,
    quantity: updatedQuantity,
    unit_type: item.unit_type,
    low_stock_threshold: item.low_stock_threshold,
    status: newStatus,
    updated_at: new Date().toISOString(),
    is_deleted: false,
    note: `Status updated to ${newStatus} on mobile`,
  };

  return recordOfflinePantryMutation(homeId, mutation);
}

export async function syncOfflineQueueToServer(
  homeId: string
): Promise<SyncStatusSummary> {
  const pendingMutations = await getPendingSyncMutations(homeId);
  const lastSyncedAt = await getLastSyncedAt(homeId);

  try {
    const resolvedHomeId = await ensureAuthenticatedHousehold(homeId);
    const syncResponse: PantrySyncResponse = await postPantryDeltaSync(
      resolvedHomeId,
      {
        last_synced_at: lastSyncedAt,
        mutations: pendingMutations,
      }
    );

    await applyServerDeltasToLocalDb(
      homeId,
      syncResponse.items.map((item) => ({ ...item, home_id: homeId })),
      syncResponse.synced_at
    );

    if (pendingMutations.length > 0) {
      await clearPendingSyncMutations(
        homeId,
        pendingMutations.map((m) => m.id)
      );
    }

    const updatedItems = await getLocalPantryItems(homeId);
    const remainingPending = await getPendingSyncMutations(homeId);

    return {
      isOnline: true,
      pendingCount: remainingPending.length,
      lastSyncedAt: syncResponse.synced_at,
      appliedCount: syncResponse.applied_mutations_count,
      items: updatedItems,
    };
  } catch {
    // Offline fallback: mutations remain queued in SQLite pending_sync table
    const localItems = await getLocalPantryItems(homeId);
    return {
      isOnline: false,
      pendingCount: pendingMutations.length,
      lastSyncedAt,
      appliedCount: 0,
      items: localItems,
    };
  }
}

export interface HouseholdBasketComparisonResult {
  basket: HouseholdBasketResponse | null;
  calculation: BasketCalculationResponse;
  isLiveBackend: boolean;
}

export async function syncAndCalculateSmartBasket(
  homeId: string,
  selectedRetailerSlugs?: string[]
): Promise<HouseholdBasketComparisonResult> {
  // 1. Flush any queued offline mutations so low/finished items bridge to basket
  const syncResult = await syncOfflineQueueToServer(homeId);

  let basket: HouseholdBasketResponse | null = null;
  let calcRequestItems: BasketItemRequest[] = [];

  if (syncResult.isOnline) {
    try {
      const resolvedHomeId = await ensureAuthenticatedHousehold(homeId);
      basket = await fetchHouseholdBasket(resolvedHomeId);
      calcRequestItems = basket.items.map((bi) => ({
        product_id: bi.product_id,
        quantity: bi.quantity,
      }));
    } catch {
      basket = null;
    }
  }

  // Derive basket items from local low/finished catalog-linked pantry items if basket not loaded
  if (calcRequestItems.length === 0) {
    const depletedCatalogItems = syncResult.items.filter(
      (item) =>
        item.product_id !== null &&
        (item.status === 'low' || item.status === 'finished') &&
        !item.is_deleted
    );

    calcRequestItems = depletedCatalogItems.map((item) => ({
      product_id: item.product_id as string,
      quantity: Math.max(parseFloat(item.low_stock_threshold) || 1, 1).toFixed(2),
    }));
  }

  // Ensure default 3-item staple basket exists for comparison if none marked low yet
  if (calcRequestItems.length === 0) {
    calcRequestItems = [
      { product_id: SEED_CATALOG_PRODUCTS.MILK_2L.id, quantity: '2.00' },
      { product_id: SEED_CATALOG_PRODUCTS.WHITE_BREAD_700G.id, quantity: '1.00' },
      { product_id: SEED_CATALOG_PRODUCTS.LARGE_EGGS_18PK.id, quantity: '1.00' },
    ];
  }

  const activeSlugs =
    selectedRetailerSlugs && selectedRetailerSlugs.length > 0
      ? selectedRetailerSlugs
      : undefined;

  try {
    const calculation = await calculateMultiStoreBasket({
      items: calcRequestItems,
      ...(activeSlugs ? { retailer_slugs: activeSlugs } : {}),
    });
    return {
      basket,
      calculation,
      isLiveBackend: true,
    };
  } catch {
    // Offline deterministic price calculation fallback matching seed catalog prices
    return {
      basket,
      calculation: buildOfflineFallbackCalculation(calcRequestItems, activeSlugs),
      isLiveBackend: false,
    };
  }
}

const OFFLINE_STAPLE_PRICES: Record<
  string,
  Record<string, { price: number; promo: boolean }>
> = {
  [SEED_CATALOG_PRODUCTS.MILK_2L.id]: {
    shoprite: { price: 33.99, promo: false },
    checkers: { price: 31.99, promo: true },
    'pick-n-pay': { price: 38.99, promo: false },
    spar: { price: 40.49, promo: false },
    'woolworths-food': { price: 42.99, promo: false },
  },
  [SEED_CATALOG_PRODUCTS.WHITE_BREAD_700G.id]: {
    shoprite: { price: 15.99, promo: false },
    checkers: { price: 17.99, promo: false },
    'pick-n-pay': { price: 16.99, promo: false },
    spar: { price: 18.49, promo: false },
    'woolworths-food': { price: 19.99, promo: false },
  },
  [SEED_CATALOG_PRODUCTS.LARGE_EGGS_18PK.id]: {
    shoprite: { price: 58.99, promo: false },
    checkers: { price: 64.99, promo: false },
    'pick-n-pay': { price: 54.99, promo: true },
    spar: { price: 66.49, promo: false },
    'woolworths-food': { price: 62.99, promo: false },
  },
};

function getOfflineProductName(productId: string): string {
  if (productId === SEED_CATALOG_PRODUCTS.MILK_2L.id) {
    return SEED_CATALOG_PRODUCTS.MILK_2L.name;
  }
  if (productId === SEED_CATALOG_PRODUCTS.WHITE_BREAD_700G.id) {
    return SEED_CATALOG_PRODUCTS.WHITE_BREAD_700G.name;
  }
  if (productId === SEED_CATALOG_PRODUCTS.LARGE_EGGS_18PK.id) {
    return SEED_CATALOG_PRODUCTS.LARGE_EGGS_18PK.name;
  }
  return 'Catalog Staple';
}

function buildOfflineFallbackCalculation(
  items: BasketItemRequest[],
  selectedSlugs?: string[]
): BasketCalculationResponse {
  const allowedChains =
    selectedSlugs && selectedSlugs.length > 0
      ? NATIONAL_RETAILER_CHAINS.filter((c) => selectedSlugs.includes(c.slug))
      : NATIONAL_RETAILER_CHAINS;

  const rankedStores = allowedChains
    .map((chain) => {
      let total = 0;
      const lineItems = items.map((item) => {
        const qty = Number(item.quantity) || 1;
        const entry = OFFLINE_STAPLE_PRICES[item.product_id]?.[chain.slug] ?? {
          price: 35.0,
          promo: false,
        };
        const subtotal = Number((entry.price * qty).toFixed(2));
        total += subtotal;
        return {
          product_id: item.product_id,
          product_name: getOfflineProductName(item.product_id),
          quantity: qty.toFixed(2),
          unit_price: entry.price.toFixed(2),
          subtotal: subtotal.toFixed(2),
          is_promotional: entry.promo,
        };
      });

      return {
        store_id: chain.store_id,
        store_name: chain.name,
        branch_code: null,
        retailer_name: chain.name,
        total_price: total.toFixed(2),
        is_complete_match: true,
        items_available_count: items.length,
        total_items_count: items.length,
        items: lineItems,
        missing_items: [],
      };
    })
    .sort((a, b) => Number(a.total_price) - Number(b.total_price));

  const cheapestSingle = rankedStores[0] ?? null;

  if (allowedChains.length < 2 || !cheapestSingle) {
    return {
      total_items_requested: items.length,
      cheapest_single_store: cheapestSingle,
      optimal_split: null,
      ranked_stores: rankedStores,
    };
  }

  // Allocate each item to the lowest-priced selected chain
  const allocMap = new Map<
    string,
    {
      chain: NationalRetailerOption;
      items: BasketCalculationResponse['ranked_stores'][number]['items'];
      subtotal: number;
    }
  >();
  let splitTotal = 0;

  for (const item of items) {
    const qty = Number(item.quantity) || 1;
    let bestChain = allowedChains[0];
    let bestPrice = Infinity;
    let bestPromo = false;

    for (const chain of allowedChains) {
      const entry = OFFLINE_STAPLE_PRICES[item.product_id]?.[chain.slug] ?? {
        price: 35.0,
        promo: false,
      };
      if (entry.price < bestPrice) {
        bestPrice = entry.price;
        bestPromo = entry.promo;
        bestChain = chain;
      }
    }

    const subtotal = Number((bestPrice * qty).toFixed(2));
    splitTotal += subtotal;

    const existing = allocMap.get(bestChain.store_id) ?? {
      chain: bestChain,
      items: [],
      subtotal: 0,
    };
    existing.items.push({
      product_id: item.product_id,
      product_name: getOfflineProductName(item.product_id),
      quantity: qty.toFixed(2),
      unit_price: bestPrice.toFixed(2),
      subtotal: subtotal.toFixed(2),
      is_promotional: bestPromo,
    });
    existing.subtotal = Number((existing.subtotal + subtotal).toFixed(2));
    allocMap.set(bestChain.store_id, existing);
  }

  const singleTotal = Number(cheapestSingle.total_price);
  const savings = Math.max(0, Number((singleTotal - splitTotal).toFixed(2)));
  const savingsPct =
    singleTotal > 0 ? ((savings / singleTotal) * 100).toFixed(2) : '0.00';

  return {
    total_items_requested: items.length,
    cheapest_single_store: cheapestSingle,
    optimal_split: {
      stores: Array.from(allocMap.values()).map((entry) => ({
        store_id: entry.chain.store_id,
        store_name: entry.chain.name,
        retailer_name: entry.chain.name,
        subtotal: entry.subtotal.toFixed(2),
        items: entry.items,
      })),
      total_price: splitTotal.toFixed(2),
      savings_amount: savings.toFixed(2),
      savings_percentage: savingsPct,
      is_complete_match: true,
      cheaper_than_single_store: savings > 0,
    },
    ranked_stores: rankedStores,
  };
}
