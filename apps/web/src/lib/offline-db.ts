/**
 * Aujasya — IndexedDB Offline Storage (v2)
 * iOS-safe: no reliance on Service Worker Background Sync API.
 * Uses idb library for clean promise-based IndexedDB access.
 *
 * v2 additions (Phase 2):
 *   - 'journal-entries' store for offline side-effect logging
 *   - 'interaction-cache' store for offline drug interaction lookup
 *   - 'generic-cache' store for offline generic drug results
 */

import { openDB, type IDBPDatabase } from 'idb';

const DB_NAME = 'aujasya-offline';
const DB_VERSION = 2;

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

// ── Phase 2 types ───────────────────────────────────────────────────────────

interface OfflineJournalEntry {
  id: string;
  medicineId: string | null;
  symptomText: string;
  severity: 'mild' | 'moderate' | 'severe';
  onsetDate: string;
  inputMethod: 'voice' | 'text';
  synced: boolean;
  createdAt: string;
}

interface CachedInteraction {
  pairKey: string; // "rxcui_a:rxcui_b" (sorted)
  severity: string;
  description: string;
  cachedAt: string;
  expiresAt: string;
}

interface CachedGenericResult {
  brandName: string;
  alternatives: unknown[];
  cachedAt: string;
  expiresAt: string;
}

type AujasyaDB = {
  'sync-queue': {
    key: string;
    value: OfflineMutation;
    indexes: Record<string, never>;
  };
  'cached-doses': {
    key: string;
    value: CachedDoseLog;
    indexes: { 'by-date': string };
  };
  // Phase 2 stores
  'journal-entries': {
    key: string;
    value: OfflineJournalEntry;
    indexes: { 'by-date': string };
  };
  'interaction-cache': {
    key: string;
    value: CachedInteraction;
    indexes: { 'by-expires': string };
  };
  'generic-cache': {
    key: string;
    value: CachedGenericResult;
    indexes: { 'by-expires': string };
  };
};

let dbInstance: IDBPDatabase<AujasyaDB> | null = null;

export async function getDB(): Promise<IDBPDatabase<AujasyaDB>> {
  if (dbInstance) return dbInstance;

  dbInstance = await openDB<AujasyaDB>(DB_NAME, DB_VERSION, {
    upgrade(db, oldVersion) {
      // v1 stores (original)
      if (oldVersion < 1) {
        // Sync queue for offline mutations
        if (!db.objectStoreNames.contains('sync-queue')) {
          db.createObjectStore('sync-queue', { keyPath: 'id' });
        }

        // Cached dose logs for offline viewing
        if (!db.objectStoreNames.contains('cached-doses')) {
          const doseStore = db.createObjectStore('cached-doses', { keyPath: 'id' });
          doseStore.createIndex('by-date', 'scheduledDate');
        }
      }

      // v2 stores (Phase 2)
      if (oldVersion < 2) {
        // Offline journal entries
        if (!db.objectStoreNames.contains('journal-entries')) {
          const journalStore = db.createObjectStore('journal-entries', { keyPath: 'id' });
          journalStore.createIndex('by-date', 'onsetDate');
        }

        // Drug interaction cache
        if (!db.objectStoreNames.contains('interaction-cache')) {
          const interactionStore = db.createObjectStore('interaction-cache', { keyPath: 'pairKey' });
          interactionStore.createIndex('by-expires', 'expiresAt');
        }

        // Generic search cache
        if (!db.objectStoreNames.contains('generic-cache')) {
          const genericStore = db.createObjectStore('generic-cache', { keyPath: 'brandName' });
          genericStore.createIndex('by-expires', 'expiresAt');
        }
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
  const items = await db.getAll('sync-queue');
  return items.filter((item) => !item.synced);
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
  const synced = (await db.getAll('sync-queue')).filter((item) => item.synced);
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

// ── Phase 2: Offline Journal Entries ────────────────────────────────────────

export async function addOfflineJournalEntry(
  entry: Omit<OfflineJournalEntry, 'id' | 'synced' | 'createdAt'>
): Promise<string> {
  const db = await getDB();
  const id = crypto.randomUUID();
  const record: OfflineJournalEntry = {
    ...entry,
    id,
    synced: false,
    createdAt: new Date().toISOString(),
  };
  await db.put('journal-entries', record);
  return id;
}

export async function getPendingJournalEntries(): Promise<OfflineJournalEntry[]> {
  const db = await getDB();
  const items = await db.getAll('journal-entries');
  return items.filter((item) => !item.synced);
}

export async function markJournalEntrySynced(id: string): Promise<void> {
  const db = await getDB();
  const entry = await db.get('journal-entries', id);
  if (entry) {
    entry.synced = true;
    await db.put('journal-entries', entry);
  }
}

// ── Phase 2: Interaction Cache (Offline) ────────────────────────────────────

export async function cacheInteraction(
  rxcuiA: string,
  rxcuiB: string,
  severity: string,
  description: string,
  ttlDays: number = 7
): Promise<void> {
  const db = await getDB();
  const [a, b] = [rxcuiA, rxcuiB].sort();
  const now = new Date();
  const expires = new Date(now.getTime() + ttlDays * 86400000);
  await db.put('interaction-cache', {
    pairKey: `${a}:${b}`,
    severity,
    description,
    cachedAt: now.toISOString(),
    expiresAt: expires.toISOString(),
  });
}

export async function getCachedInteraction(
  rxcuiA: string,
  rxcuiB: string
): Promise<CachedInteraction | null> {
  const db = await getDB();
  const [a, b] = [rxcuiA, rxcuiB].sort();
  const entry = await db.get('interaction-cache', `${a}:${b}`);
  if (entry && new Date(entry.expiresAt) > new Date()) {
    return entry;
  }
  return null;
}

// ── Phase 2: Generic Cache (Offline) ────────────────────────────────────────

export async function cacheGenericResult(
  brandName: string,
  alternatives: unknown[],
  ttlHours: number = 24
): Promise<void> {
  const db = await getDB();
  const now = new Date();
  const expires = new Date(now.getTime() + ttlHours * 3600000);
  await db.put('generic-cache', {
    brandName: brandName.toLowerCase(),
    alternatives,
    cachedAt: now.toISOString(),
    expiresAt: expires.toISOString(),
  });
}

export async function getCachedGenericResult(
  brandName: string
): Promise<CachedGenericResult | null> {
  const db = await getDB();
  const entry = await db.get('generic-cache', brandName.toLowerCase());
  if (entry && new Date(entry.expiresAt) > new Date()) {
    return entry;
  }
  return null;
}
