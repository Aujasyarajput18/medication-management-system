/**
 * Aujasya — IndexedDB Storage Quota Monitor
 * Checks navigator.storage.estimate() on app start.
 * Degradation order: 1) pill model cache  2) generic cache  3) interaction cache
 * NEVER purges: sync-queue, cached-doses (critical offline functionality)
 */

import { purgeModelCache, getModelCacheSize } from '@/lib/ml/model-cache';

export interface StorageStatus {
  status: 'ok' | 'low' | 'critical' | 'unknown';
  remainingMB: number;
  usageMB: number;
  quotaMB: number;
  action?: 'none' | 'disable_model_cache' | 'purge_all_caches';
}

const LOW_THRESHOLD_MB = 20;
const CRITICAL_THRESHOLD_MB = 10;

/**
 * Check available storage quota and return status with recommended action.
 * Called from OnlineStatusProvider on app mount.
 */
export async function checkStorageQuota(): Promise<StorageStatus> {
  if (!navigator.storage?.estimate) {
    return { status: 'unknown', remainingMB: 0, usageMB: 0, quotaMB: 0 };
  }

  try {
    const { usage, quota } = await navigator.storage.estimate();
    const usageMB = (usage ?? 0) / (1024 * 1024);
    const quotaMB = (quota ?? 0) / (1024 * 1024);
    const remainingMB = quotaMB - usageMB;

    if (remainingMB < CRITICAL_THRESHOLD_MB) {
      return {
        status: 'critical',
        remainingMB: Math.round(remainingMB * 10) / 10,
        usageMB: Math.round(usageMB * 10) / 10,
        quotaMB: Math.round(quotaMB * 10) / 10,
        action: 'purge_all_caches',
      };
    }

    if (remainingMB < LOW_THRESHOLD_MB) {
      return {
        status: 'low',
        remainingMB: Math.round(remainingMB * 10) / 10,
        usageMB: Math.round(usageMB * 10) / 10,
        quotaMB: Math.round(quotaMB * 10) / 10,
        action: 'disable_model_cache',
      };
    }

    return {
      status: 'ok',
      remainingMB: Math.round(remainingMB * 10) / 10,
      usageMB: Math.round(usageMB * 10) / 10,
      quotaMB: Math.round(quotaMB * 10) / 10,
      action: 'none',
    };
  } catch {
    return { status: 'unknown', remainingMB: 0, usageMB: 0, quotaMB: 0 };
  }
}

/**
 * Execute progressive cache degradation based on storage status.
 * Degradation priority (first to purge → last):
 *   1. Pill model cache (largest, ~20MB)
 *   2. Generic search cache (via caches API)
 *   3. Drug interaction cache (via caches API)
 *   ✗ sync-queue — NEVER purged (offline mutations)
 *   ✗ cached-doses — NEVER purged (offline viewing)
 */
export async function executeStorageDegradation(
  status: StorageStatus
): Promise<void> {
  if (status.action === 'disable_model_cache' || status.action === 'purge_all_caches') {
    // Step 1: Always purge model cache first (largest)
    await purgeModelCache();
    console.warn('[StorageQuota] Purged pill model cache');
  }

  if (status.action === 'purge_all_caches') {
    // Step 2: Purge generic search cache
    try {
      await caches.delete('aujasya-generic-cache-v1');
      console.warn('[StorageQuota] Purged generic search cache');
    } catch { /* cache may not exist */ }

    // Step 3: Purge interaction cache
    try {
      await caches.delete('aujasya-interaction-cache-v1');
      console.warn('[StorageQuota] Purged interaction cache');
    } catch { /* cache may not exist */ }
  }
}

/**
 * Should model caching be enabled? Returns false when storage is low.
 */
export async function isModelCachingAllowed(): Promise<boolean> {
  const status = await checkStorageQuota();
  return status.status === 'ok';
}
