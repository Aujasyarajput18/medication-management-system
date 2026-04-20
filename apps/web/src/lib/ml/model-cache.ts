/**
 * Aujasya — Model Cache Management
 * Cache-First strategy for ML model files via Service Worker Cache API.
 * Integrates with storage-quota.ts to disable caching when storage is low.
 */

const MODEL_CACHE_NAME = 'aujasya-ml-models-v1';

/**
 * Check if a model is cached in the Service Worker cache.
 */
export async function isModelCached(modelUrl: string): Promise<boolean> {
  try {
    const cache = await caches.open(MODEL_CACHE_NAME);
    const response = await cache.match(modelUrl);
    return response !== undefined;
  } catch {
    return false;
  }
}

/**
 * Cache a model file. Respects storage quota limits.
 */
export async function cacheModel(
  modelUrl: string,
  response: Response
): Promise<void> {
  try {
    const cache = await caches.open(MODEL_CACHE_NAME);
    await cache.put(modelUrl, response.clone());
  } catch (error) {
    console.warn('[ModelCache] Failed to cache model:', error);
  }
}

/**
 * Get a cached model response, or null if not cached.
 */
export async function getCachedModel(
  modelUrl: string
): Promise<Response | null> {
  try {
    const cache = await caches.open(MODEL_CACHE_NAME);
    const response = await cache.match(modelUrl);
    return response || null;
  } catch {
    return null;
  }
}

/**
 * Purge the model cache. Called by storage-quota.ts when storage is low.
 * This is the FIRST cache to be purged in the degradation order.
 */
export async function purgeModelCache(): Promise<void> {
  try {
    await caches.delete(MODEL_CACHE_NAME);
    console.log('[ModelCache] Purged model cache');
  } catch (error) {
    console.warn('[ModelCache] Failed to purge:', error);
  }
}

/**
 * Get the total size of cached models in bytes.
 */
export async function getModelCacheSize(): Promise<number> {
  try {
    const cache = await caches.open(MODEL_CACHE_NAME);
    const keys = await cache.keys();
    let totalSize = 0;
    for (const request of keys) {
      const response = await cache.match(request);
      if (response) {
        const blob = await response.blob();
        totalSize += blob.size;
      }
    }
    return totalSize;
  } catch {
    return 0;
  }
}
