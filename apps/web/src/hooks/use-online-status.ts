/**
 * Aujasya — Online Status Hook
 * Detects online/offline state and triggers offline sync.
 *
 * [FIX-8] This is the PRIMARY sync mechanism on iOS Safari.
 * Background Sync API is NOT supported on iOS, so this hook
 * acts as the fallback: when the device comes back online,
 * we immediately flush the IndexedDB sync queue via the API.
 *
 * On Android/Chrome, Background Sync may also fire — that's fine,
 * double-sync is idempotent (server uses ON CONFLICT DO NOTHING).
 */

import { useState, useEffect, useCallback } from 'react';
import { useDoseStore } from '@/stores/dose-store';

export function useOnlineStatus() {
  const [isOnline, setIsOnline] = useState(
    typeof navigator !== 'undefined' ? navigator.onLine : true
  );
  const syncOffline = useDoseStore((s) => s.syncOffline);

  const handleOnline = useCallback(() => {
    setIsOnline(true);

    // [FIX-8] Primary sync trigger on iOS, secondary on Android.
    // 1. Flush IndexedDB sync queue via API
    syncOffline().catch(() => {});

    // 2. Attempt to register Background Sync (Chrome/Android only).
    //    On iOS this throws — we catch and ignore.
    if ('serviceWorker' in navigator && 'SyncManager' in window) {
      navigator.serviceWorker.ready
        .then((reg) => {
          try {
            return (reg as any).sync.register('sync-doses');
          } catch {
            // iOS or permission denied — step 1 already handles it
          }
        })
        .catch(() => {
          // SW not ready — step 1 already handles it
        });
    }
  }, [syncOffline]);

  const handleOffline = useCallback(() => {
    setIsOnline(false);
  }, []);

  useEffect(() => {
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // [FIX-8] Listen for SW postMessage (offline notification-click dose queue)
    const handleSWMessage = (event: MessageEvent) => {
      if (event.data?.type === 'QUEUE_OFFLINE_DOSE') {
        import('@/lib/offline-db').then(({ addToSyncQueue }) => {
          addToSyncQueue({
            doseId: event.data.doseId,
            action: event.data.action,
            deviceTimestamp: new Date().toISOString(),
          });
        });
      }
    };
    navigator.serviceWorker?.addEventListener('message', handleSWMessage);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
      navigator.serviceWorker?.removeEventListener('message', handleSWMessage);
    };
  }, [handleOnline, handleOffline]);

  return isOnline;
}
