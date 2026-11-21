/**
 * Global sync status & cached basket comparison context powering:
 * - Subtle top Sync Status Pill (Synced vs. Syncing vs. Offline) across all 3 tabs
 * - Data-saving cached Basket comparison state persisted in SQLite / localStorage
 *   so switching to the Basket tab renders immediately without redundant API calls.
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';

import {
  getCachedBasketComparisonRaw,
  setCachedBasketComparisonRaw,
} from '@/db/sqlite';
import { getApiBaseUrl } from '@/services/api';
import {
  type HouseholdBasketComparisonResult,
  NATIONAL_RETAILER_CHAINS,
} from '@/services/sync';

export type SyncState = 'synced' | 'syncing' | 'offline';

export interface CachedBasketSnapshot {
  comparison: HouseholdBasketComparisonResult;
  selectedSlugs: string[];
  calculatedAt: string;
}

const DEFAULT_SELECTED_SLUGS = NATIONAL_RETAILER_CHAINS.map((c) => c.slug);

export interface SyncStatusContextValue {
  status: SyncState;
  pendingCount: number;
  lastSyncedAt: string | null;
  catalogLastSyncAt: string | null;
  trackedPricesCount: number | null;
  latestComparison: HouseholdBasketComparisonResult | null;
  lastCalculatedAt: string | null;
  selectedRetailerSlugs: string[];
  isCacheHydrated: boolean;
  setLatestComparison: (
    result: HouseholdBasketComparisonResult | null,
    selectedSlugs?: string[]
  ) => void;
  setSelectedRetailerSlugs: (slugs: string[]) => void;
  setSyncState: (update: {
    status?: SyncState;
    pendingCount?: number;
    lastSyncedAt?: string | null;
  }) => void;
  probeBackendHealth: () => Promise<boolean>;
}

const SyncStatusContext = createContext<SyncStatusContextValue | null>(null);

export function SyncStatusProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<SyncState>('offline');
  const [pendingCount, setPendingCount] = useState<number>(0);
  const [lastSyncedAt, setLastSyncedAt] = useState<string | null>(null);
  const [catalogLastSyncAt, setCatalogLastSyncAt] = useState<string | null>(null);
  const [trackedPricesCount, setTrackedPricesCount] = useState<number | null>(null);
  const [latestComparison, setLatestComparisonState] =
    useState<HouseholdBasketComparisonResult | null>(null);
  const [lastCalculatedAt, setLastCalculatedAt] = useState<string | null>(null);
  const [selectedRetailerSlugs, setSelectedRetailerSlugs] = useState<string[]>(
    DEFAULT_SELECTED_SLUGS
  );
  const [isCacheHydrated, setIsCacheHydrated] = useState<boolean>(false);

  // Hydrate persisted cached basket comparison on mount (zero API calls)
  useEffect(() => {
    let mounted = true;
    void (async () => {
      try {
        const raw = await getCachedBasketComparisonRaw();
        if (mounted && raw) {
          const parsed = JSON.parse(raw) as Partial<CachedBasketSnapshot>;
          if (parsed.comparison && parsed.calculatedAt) {
            setLatestComparisonState(parsed.comparison);
            setLastCalculatedAt(parsed.calculatedAt);
            if (
              Array.isArray(parsed.selectedSlugs) &&
              parsed.selectedSlugs.length > 0
            ) {
              setSelectedRetailerSlugs(parsed.selectedSlugs);
            }
          }
        }
      } catch {
        // Ignore malformed cache entries
      } finally {
        if (mounted) {
          setIsCacheHydrated(true);
        }
      }
    })();

    return () => {
      mounted = false;
    };
  }, []);

  const setLatestComparison = useCallback(
    (
      result: HouseholdBasketComparisonResult | null,
      slugsOverride?: string[]
    ) => {
      setLatestComparisonState(result);
      if (slugsOverride && slugsOverride.length > 0) {
        setSelectedRetailerSlugs(slugsOverride);
      }

      if (!result) {
        setLastCalculatedAt(null);
        return;
      }

      const calculatedAt = new Date().toISOString();
      setLastCalculatedAt(calculatedAt);
      const slugsToSave =
        slugsOverride && slugsOverride.length > 0
          ? slugsOverride
          : selectedRetailerSlugs;

      const snapshot: CachedBasketSnapshot = {
        comparison: result,
        selectedSlugs: slugsToSave,
        calculatedAt,
      };
      void setCachedBasketComparisonRaw(JSON.stringify(snapshot));
    },
    [selectedRetailerSlugs]
  );

  const setSyncState = useCallback(
    (update: {
      status?: SyncState;
      pendingCount?: number;
      lastSyncedAt?: string | null;
    }) => {
      if (update.status !== undefined) {
        setStatus(update.status);
      }
      if (update.pendingCount !== undefined) {
        setPendingCount(update.pendingCount);
      }
      if (update.lastSyncedAt !== undefined) {
        setLastSyncedAt(update.lastSyncedAt);
      }
    },
    []
  );

  const probeBackendHealth = useCallback(async (): Promise<boolean> => {
    try {
      const apiBase = getApiBaseUrl();
      const healthUrl = apiBase.replace(/\/api\/v1$/, '/health');
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 3500);
      const response = await fetch(healthUrl, {
        headers: { Accept: 'application/json' },
        signal: controller.signal,
      });
      clearTimeout(timeoutId);

      if (!response.ok) {
        setStatus('offline');
        return false;
      }

      const data = (await response.json()) as {
        status?: string;
        catalog_freshness?: {
          last_price_sync_at?: string | null;
          tracked_prices?: number;
        };
      };

      if (data.catalog_freshness) {
        setCatalogLastSyncAt(data.catalog_freshness.last_price_sync_at ?? null);
        if (typeof data.catalog_freshness.tracked_prices === 'number') {
          setTrackedPricesCount(data.catalog_freshness.tracked_prices);
        }
      }
      setStatus((prev) => (prev === 'syncing' ? prev : 'synced'));
      return true;
    } catch {
      setStatus('offline');
      return false;
    }
  }, []);

  useEffect(() => {
    void probeBackendHealth();
  }, [probeBackendHealth]);

  const value = useMemo<SyncStatusContextValue>(
    () => ({
      status,
      pendingCount,
      lastSyncedAt,
      catalogLastSyncAt,
      trackedPricesCount,
      latestComparison,
      lastCalculatedAt,
      selectedRetailerSlugs,
      isCacheHydrated,
      setLatestComparison,
      setSelectedRetailerSlugs,
      setSyncState,
      probeBackendHealth,
    }),
    [
      status,
      pendingCount,
      lastSyncedAt,
      catalogLastSyncAt,
      trackedPricesCount,
      latestComparison,
      lastCalculatedAt,
      selectedRetailerSlugs,
      isCacheHydrated,
      setLatestComparison,
      setSyncState,
      probeBackendHealth,
    ]
  );

  return (
    <SyncStatusContext.Provider value={value}>
      {children}
    </SyncStatusContext.Provider>
  );
}

export function useSyncStatus(): SyncStatusContextValue {
  const ctx = useContext(SyncStatusContext);
  if (!ctx) {
    return {
      status: 'offline',
      pendingCount: 0,
      lastSyncedAt: null,
      catalogLastSyncAt: null,
      trackedPricesCount: null,
      latestComparison: null,
      lastCalculatedAt: null,
      selectedRetailerSlugs: DEFAULT_SELECTED_SLUGS,
      isCacheHydrated: true,
      setLatestComparison: () => undefined,
      setSelectedRetailerSlugs: () => undefined,
      setSyncState: () => undefined,
      probeBackendHealth: async () => false,
    };
  }
  return ctx;
}
