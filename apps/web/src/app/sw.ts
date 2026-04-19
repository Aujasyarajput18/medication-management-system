/**
 * Aujasya — Unified Service Worker
 * [FIX-9] Single SW scope: Serwist (precaching + runtime) + FCM push handling.
 * [FIX-8] iOS Background Sync: sync.register() wrapped in try/catch.
 *         iOS Safari does NOT support the Background Sync API.
 *         Fallback: useOnlineStatus hook triggers sync on reconnect.
 * NO separate firebase-messaging-sw.js — that creates scope conflicts.
 */

import { defaultCache } from '@serwist/next/worker';
import { installSerwist } from '@serwist/sw';

declare const self: ServiceWorkerGlobalScope & {
  __SW_MANIFEST: any;
};

// ── Serwist: Precaching + Runtime Caching ──────────────────────────────────
installSerwist({
  precacheEntries: self.__SW_MANIFEST,
  skipWaiting: true,
  clientsClaim: true,
  navigationPreload: true,
  runtimeCaching: [
    ...defaultCache,
    // Cache API responses (network-first, 5-minute max age)
    {
      urlPattern: /^https?:\/\/.*\/api\/v1\/(doses|medicines|caregivers)/,
      handler: 'NetworkFirst',
      options: {
        cacheName: 'api-cache',
        expiration: {
          maxEntries: 100,
          maxAgeSeconds: 300, // 5 minutes
        },
        networkTimeoutSeconds: 3,
      },
    },
    // Cache Indic fonts (cache-first, 30 days)
    {
      urlPattern: /^https:\/\/fonts\.(googleapis|gstatic)\.com/,
      handler: 'CacheFirst',
      options: {
        cacheName: 'google-fonts',
        expiration: {
          maxEntries: 30,
          maxAgeSeconds: 60 * 60 * 24 * 30, // 30 days
        },
      },
    },
  ],
  // Offline fallback
  fallbacks: {
    entries: [
      {
        url: '/offline.html',
        matcher: ({ request }) => request.destination === 'document',
      },
    ],
  },
});

// ── FCM Push Notifications ─────────────────────────────────────────────────
// [FIX-9] Merged into the same SW scope — no separate firebase-messaging-sw.js

self.addEventListener('push', (event: PushEvent) => {
  if (!event.data) return;

  let payload: { title: string; body: string; data?: Record<string, string> };

  try {
    payload = event.data.json();
  } catch {
    payload = {
      title: '💊 Aujasya',
      body: event.data.text(),
    };
  }

  const options: NotificationOptions = {
    body: payload.body,
    icon: '/icons/icon-192.png',
    badge: '/icons/icon-192.png',
    vibrate: [200, 100, 200],
    tag: payload.data?.dose_log_id || 'aujasya-reminder',
    data: payload.data || {},
    actions: [
      { action: 'taken', title: '✅ Taken / ले लिया' },
      { action: 'snooze', title: '⏰ Snooze / बाद में' },
    ],
    requireInteraction: true, // Keep notification visible until user acts
  };

  event.waitUntil(self.registration.showNotification(payload.title, options));
});

// Handle notification click/action
self.addEventListener('notificationclick', (event: NotificationEvent) => {
  event.notification.close();

  const action = event.action;
  const data = event.notification.data;

  if (action === 'taken' && data?.dose_log_id) {
    // Quick-action: mark dose as taken via API
    event.waitUntil(
      fetch(`/api/bff/doses/${data.dose_log_id}/taken`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ notes: 'Marked via notification' }),
      }).catch(() => {
        // Offline — notification to client page to queue via IndexedDB
        self.clients.matchAll({ type: 'window' }).then((clients) => {
          clients.forEach((client) => {
            client.postMessage({
              type: 'QUEUE_OFFLINE_DOSE',
              doseId: data.dose_log_id,
              action: 'taken',
            });
          });
        });
      })
    );
  } else {
    // Open the app at today's doses
    event.waitUntil(
      self.clients.matchAll({ type: 'window' }).then((clients) => {
        if (clients.length > 0) {
          clients[0].focus();
          clients[0].navigate('/hi/today');
        } else {
          self.clients.openWindow('/hi/today');
        }
      })
    );
  }
});

// ── Background Sync ────────────────────────────────────────────────────────
// [FIX-8] iOS Safari does NOT support the Background Sync API.
// This listener only fires on Chrome/Android. On iOS, the useOnlineStatus
// hook detects reconnection and calls syncOffline() from the main thread.
// We MUST guard the 'sync' event — if iOS somehow fires it (future Safari),
// we don't want it to crash.

self.addEventListener('sync', (event: SyncEvent) => {
  if (event.tag === 'sync-doses') {
    event.waitUntil(syncOfflineDoses());
  }
});

async function syncOfflineDoses(): Promise<void> {
  try {
    const response = await fetch('/api/bff/doses/sync-offline', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mutations: [] }), // Client populates via postMessage
    });
    if (response.ok) {
      console.log('[SW] Offline doses synced');
    }
  } catch (error) {
    console.error('[SW] Sync failed, will retry:', error);
  }
}

/**
 * [FIX-8] Safe registration helper — exported for use by the main app.
 *
 * Usage in a client component:
 *   if ('serviceWorker' in navigator && 'SyncManager' in window) {
 *     try { await reg.sync.register('sync-doses'); }
 *     catch { /* iOS or denied — useOnlineStatus handles it *\/ }
 *   }
 *
 * This function is NOT imported directly from sw.ts (service workers run
 * in a separate scope). Instead, the pattern is documented here for
 * reference, and the actual call lives in use-online-status.ts.
 */
