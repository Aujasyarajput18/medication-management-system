/**
 * Aujasya — IndexedDB Offline Storage
 * iOS-safe: no reliance on Service Worker Background Sync API.
 * Uses idb library for clean promise-based IndexedDB access.
 */

import { openDB, type IDBPDatabase } from 'idb';

const DB_NAME = 'aujasya-offline';
const DB_VERSION = 1;

interface OfflineMutation {
  id: string;
  doseId: string;
  action: 'taken' | 'skipped';
  deviceTimestamp: string;
  notes?: string;
  skipReason?: string;
  synced: boolean;
  createdAt: string;
}

interface CachedDoseLog {
  id: string;
  scheduleId: string;
  medicineId: string;
  scheduledDate: string;
  mealAnchor: string;
  status: string;
  medicineName?: string;
  dosageValue?: number;
  dosageUnit?: string;
  cachedAt: string;
}

type AujasyaDB = {
  'sync-queue': {
    key: string;
    value: OfflineMutation;
    indexes: { 'by-synced': boolean };
  };
  'cached-doses': {
    key: string;
    value: CachedDoseLog;
    indexes: { 'by-date': string };
  };
};

let dbInstance: IDBPDatabase<AujasyaDB> | null = null;

export async function getDB(): Promise<IDBPDatabase<AujasyaDB>> {
  if (dbInstance) return dbInstance;

  dbInstance = await openDB<AujasyaDB>(DB_NAME, DB_VERSION, {
    upgrade(db) {
      // Sync queue for offline mutations
      if (!db.objectStoreNames.contains('sync-queue')) {
        const syncStore = db.createObjectStore('sync-queue', { keyPath: 'id' });
        syncStore.createIndex('by-synced', 'synced');
      }

      // Cached dose logs for offline viewing
      if (!db.objectStoreNames.contains('cached-doses')) {
        const doseStore = db.createObjectStore('cached-doses', { keyPath: 'id' });
        doseStore.createIndex('by-date', 'scheduledDate');
      }
    },
  });

  return dbInstance;
}

// ── Sync Queue Operations ──────────────────────────────────────────────────

export async function addToSyncQueue(mutation: Omit<OfflineMutation, 'id' | 'synced' | 'createdAt'>): Promise<string> {
  const db = await getDB();
  const id = crypto.randomUUID();
  const entry: OfflineMutation = {
    ...mutation,
    id,
    synced: false,
    createdAt: new Date().toISOString(),
  };
  await db.put('sync-queue', entry);
  return id;
}

export async function getPendingSyncItems(): Promise<OfflineMutation[]> {
  const db = await getDB();
  return db.getAllFromIndex('sync-queue', 'by-synced', false);
}

export async function markSynced(id: string): Promise<void> {
  const db = await getDB();
  const entry = await db.get('sync-queue', id);
  if (entry) {
    entry.synced = true;
    await db.put('sync-queue', entry);
  }
}

export async function clearSyncedItems(): Promise<void> {
  const db = await getDB();
  const synced = await db.getAllFromIndex('sync-queue', 'by-synced', true);
  const tx = db.transaction('sync-queue', 'readwrite');
  for (const item of synced) {
    await tx.store.delete(item.id);
  }
  await tx.done;
}

// ── Cached Doses Operations ────────────────────────────────────────────────

export async function cacheDoses(doses: CachedDoseLog[]): Promise<void> {
  const db = await getDB();
  const tx = db.transaction('cached-doses', 'readwrite');
  for (const dose of doses) {
    await tx.store.put({ ...dose, cachedAt: new Date().toISOString() });
  }
  await tx.done;
}

export async function getCachedDosesByDate(date: string): Promise<CachedDoseLog[]> {
  const db = await getDB();
  return db.getAllFromIndex('cached-doses', 'by-date', date);
}

export async function updateCachedDoseStatus(
  doseId: string,
  status: string
): Promise<void> {
  const db = await getDB();
  const dose = await db.get('cached-doses', doseId);
  if (dose) {
    dose.status = status;
    await db.put('cached-doses', dose);
  }
}
