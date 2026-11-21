/**
 * Global sync status context powering the subtle top Sync Status Pill
 * (Synced vs. Syncing vs. Offline) across all 3 navigation tabs.
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';

import { getApiBaseUrl } from '@/services/api';
import { type HouseholdBasketComparisonResult } from '@/services/sync';

export type SyncState = 'synced' | 'syncing' | 'offline';

export interface SyncStatusContextValue {
  status: SyncState;
  pendingCount: number;
  lastSyncedAt: string | null;
  catalogLastSyncAt: string | null;
  trackedPricesCount: number | null;
  latestComparison: HouseholdBasketComparisonResult | null;
  setLatestComparison: (result: HouseholdBasketComparisonResult | null) => void;
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
  const [latestComparison, setLatestComparison] =
    useState<HouseholdBasketComparisonResult | null>(null);

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
      setLatestComparison,
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
      setLatestComparison: () => undefined,
      setSyncState: () => undefined,
      probeBackendHealth: async () => false,
    };
  }
  return ctx;
}
