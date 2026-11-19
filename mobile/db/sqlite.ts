/**
 * Local SQLite database layer (react-native-sqlite-storage) for offline-first
 * pantry persistence and delta-sync mutation queuing.
 *
 * Includes a seamless in-memory store fallback when running on Web or test runtimes
 * where the native SQLite bridge is unavailable.
 */

import { NativeModules, Platform } from 'react-native';
import SQLite, { SQLiteDatabase } from 'react-native-sqlite-storage';

import { PantryItemResponse, PantryStatus, PantrySyncMutation } from '@/types/api';

const DB_NAME = 'smartbasket_pantry.db';

export const CREATE_PANTRY_TABLE_SQL = `
  CREATE TABLE IF NOT EXISTS local_pantry_items (
    id TEXT PRIMARY KEY NOT NULL,
    home_id TEXT NOT NULL,
    product_id TEXT,
    category_id TEXT,
    custom_name TEXT,
    barcode TEXT,
    quantity TEXT NOT NULL,
    unit_type TEXT NOT NULL,
    low_stock_threshold TEXT NOT NULL,
    status TEXT NOT NULL,
    is_deleted INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL,
    product_name TEXT,
    category_name TEXT
  );
`;

export const CREATE_PENDING_SYNC_TABLE_SQL = `
  CREATE TABLE IF NOT EXISTS pending_sync (
    id TEXT PRIMARY KEY NOT NULL,
    home_id TEXT NOT NULL,
    product_id TEXT,
    category_id TEXT,
    custom_name TEXT,
    barcode TEXT,
    quantity TEXT NOT NULL,
    unit_type TEXT NOT NULL,
    low_stock_threshold TEXT NOT NULL,
    status TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    is_deleted INTEGER NOT NULL DEFAULT 0,
    note TEXT
  );
`;

export const CREATE_SYNC_META_TABLE_SQL = `
  CREATE TABLE IF NOT EXISTS sync_meta (
    home_id TEXT PRIMARY KEY NOT NULL,
    last_synced_at TEXT
  );
`;

let dbInstance: SQLiteDatabase | null = null;
let useInMemoryFallback = false;

// In-memory store fallback for web / test environments without native SQLite bridge
const memoryPantryItems = new Map<string, PantryItemResponse>();
const memoryPendingSync = new Map<string, { homeId: string; mutation: PantrySyncMutation }>();
const memorySyncMeta = new Map<string, string>();

export async function initLocalDatabase(): Promise<SQLiteDatabase | null> {
  if (dbInstance) {
    return dbInstance;
  }
  if (useInMemoryFallback) {
    return null;
  }

  try {
    if (
      Platform.OS === 'web' ||
      !NativeModules?.SQLite ||
      !SQLite ||
      typeof SQLite.openDatabase !== 'function'
    ) {
      useInMemoryFallback = true;
      return null;
    }
    SQLite.enablePromise(true);
    const db = await SQLite.openDatabase({
      name: DB_NAME,
      location: 'default',
    });

    await db.executeSql(CREATE_PANTRY_TABLE_SQL);
    await db.executeSql(CREATE_PENDING_SYNC_TABLE_SQL);
    await db.executeSql(CREATE_SYNC_META_TABLE_SQL);

    dbInstance = db;
    return dbInstance;
  } catch {
    useInMemoryFallback = true;
    return null;
  }
}

export async function getLocalPantryItems(homeId: string): Promise<PantryItemResponse[]> {
  const db = await initLocalDatabase();
  if (!db) {
    return Array.from(memoryPantryItems.values()).filter(
      (item) => item.home_id === homeId && !item.is_deleted
    );
  }

  const [results] = await db.executeSql(
    `SELECT * FROM local_pantry_items WHERE home_id = ? AND is_deleted = 0 ORDER BY updated_at DESC;`,
    [homeId]
  );

  const items: PantryItemResponse[] = [];
  for (let i = 0; i < results.rows.length; i += 1) {
    const row = results.rows.item(i);
    items.push({
      id: String(row.id),
      home_id: String(row.home_id),
      product_id: row.product_id ? String(row.product_id) : null,
      category_id: row.category_id ? String(row.category_id) : null,
      custom_name: row.custom_name ? String(row.custom_name) : null,
      barcode: row.barcode ? String(row.barcode) : null,
      quantity: String(row.quantity),
      unit_type: String(row.unit_type),
      low_stock_threshold: String(row.low_stock_threshold),
      status: String(row.status) as PantryStatus,
      is_deleted: Number(row.is_deleted) === 1,
      updated_at: String(row.updated_at),
      product_name: row.product_name ? String(row.product_name) : null,
      category_name: row.category_name ? String(row.category_name) : null,
    });
  }
  return items;
}

export async function upsertLocalPantryItem(item: PantryItemResponse): Promise<void> {
  memoryPantryItems.set(item.id, item);

  const db = await initLocalDatabase();
  if (!db) {
    return;
  }

  await db.executeSql(
    `INSERT OR REPLACE INTO local_pantry_items (
      id, home_id, product_id, category_id, custom_name, barcode,
      quantity, unit_type, low_stock_threshold, status, is_deleted,
      updated_at, product_name, category_name
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);`,
    [
      item.id,
      item.home_id,
      item.product_id,
      item.category_id,
      item.custom_name,
      item.barcode,
      item.quantity,
      item.unit_type,
      item.low_stock_threshold,
      item.status,
      item.is_deleted ? 1 : 0,
      item.updated_at,
      item.product_name,
      item.category_name,
    ]
  );
}

export async function enqueuePendingSync(
  homeId: string,
  mutation: PantrySyncMutation
): Promise<void> {
  memoryPendingSync.set(mutation.id, { homeId, mutation });

  // Also reflect optimistic change in local pantry cache immediately
  const existing = memoryPantryItems.get(mutation.id);
  const optimisticItem: PantryItemResponse = {
    id: mutation.id,
    home_id: homeId,
    product_id: mutation.product_id ?? existing?.product_id ?? null,
    category_id: mutation.category_id ?? existing?.category_id ?? null,
    custom_name: mutation.custom_name ?? existing?.custom_name ?? null,
    barcode: mutation.barcode ?? existing?.barcode ?? null,
    quantity: mutation.quantity,
    unit_type: mutation.unit_type,
    low_stock_threshold: mutation.low_stock_threshold,
    status: mutation.status,
    is_deleted: mutation.is_deleted,
    updated_at: mutation.updated_at,
    product_name: existing?.product_name ?? null,
    category_name: existing?.category_name ?? null,
  };
  await upsertLocalPantryItem(optimisticItem);

  const db = await initLocalDatabase();
  if (!db) {
    return;
  }

  await db.executeSql(
    `INSERT OR REPLACE INTO pending_sync (
      id, home_id, product_id, category_id, custom_name, barcode,
      quantity, unit_type, low_stock_threshold, status, updated_at,
      is_deleted, note
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);`,
    [
      mutation.id,
      homeId,
      mutation.product_id ?? null,
      mutation.category_id ?? null,
      mutation.custom_name ?? null,
      mutation.barcode ?? null,
      mutation.quantity,
      mutation.unit_type,
      mutation.low_stock_threshold,
      mutation.status,
      mutation.updated_at,
      mutation.is_deleted ? 1 : 0,
      mutation.note ?? null,
    ]
  );
}

export async function getPendingSyncMutations(
  homeId: string
): Promise<PantrySyncMutation[]> {
  const db = await initLocalDatabase();
  if (!db) {
    return Array.from(memoryPendingSync.values())
      .filter((entry) => entry.homeId === homeId)
      .map((entry) => entry.mutation);
  }

  const [results] = await db.executeSql(
    `SELECT * FROM pending_sync WHERE home_id = ? ORDER BY updated_at ASC;`,
    [homeId]
  );

  const mutations: PantrySyncMutation[] = [];
  for (let i = 0; i < results.rows.length; i += 1) {
    const row = results.rows.item(i);
    mutations.push({
      id: String(row.id),
      product_id: row.product_id ? String(row.product_id) : null,
      category_id: row.category_id ? String(row.category_id) : null,
      custom_name: row.custom_name ? String(row.custom_name) : null,
      barcode: row.barcode ? String(row.barcode) : null,
      quantity: String(row.quantity),
      unit_type: String(row.unit_type),
      low_stock_threshold: String(row.low_stock_threshold),
      status: String(row.status) as PantryStatus,
      updated_at: String(row.updated_at),
      is_deleted: Number(row.is_deleted) === 1,
      note: row.note ? String(row.note) : null,
    });
  }
  return mutations;
}

export async function clearPendingSyncMutations(
  homeId: string,
  mutationIds: string[]
): Promise<void> {
  for (const id of mutationIds) {
    memoryPendingSync.delete(id);
  }

  const db = await initLocalDatabase();
  if (!db || mutationIds.length === 0) {
    return;
  }

  const placeholders = mutationIds.map(() => '?').join(', ');
  await db.executeSql(
    `DELETE FROM pending_sync WHERE home_id = ? AND id IN (${placeholders});`,
    [homeId, ...mutationIds]
  );
}

export async function getLastSyncedAt(homeId: string): Promise<string | null> {
  const db = await initLocalDatabase();
  if (!db) {
    return memorySyncMeta.get(homeId) ?? null;
  }

  const [results] = await db.executeSql(
    `SELECT last_synced_at FROM sync_meta WHERE home_id = ? LIMIT 1;`,
    [homeId]
  );

  if (results.rows.length === 0) {
    return null;
  }
  const val = results.rows.item(0).last_synced_at;
  return val ? String(val) : null;
}

export async function setLastSyncedAt(
  homeId: string,
  syncedAt: string
): Promise<void> {
  memorySyncMeta.set(homeId, syncedAt);

  const db = await initLocalDatabase();
  if (!db) {
    return;
  }

  await db.executeSql(
    `INSERT OR REPLACE INTO sync_meta (home_id, last_synced_at) VALUES (?, ?);`,
    [homeId, syncedAt]
  );
}

export async function applyServerDeltasToLocalDb(
  homeId: string,
  deltas: PantryItemResponse[],
  syncedAt: string
): Promise<void> {
  for (const delta of deltas) {
    await upsertLocalPantryItem(delta);
  }
  await setLastSyncedAt(homeId, syncedAt);
}
