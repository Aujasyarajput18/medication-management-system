'use client';

/**
 * Aujasya — Online Status Provider
 * Layout-level client component that initializes the useOnlineStatus hook.
 * [FIX-8] Must be in the locale layout so it persists across navigations
 * and can trigger offline sync on reconnect at any time.
 */

import { useOnlineStatus } from '@/hooks/use-online-status';

export function OnlineStatusProvider() {
  const isOnline = useOnlineStatus();

  // Render nothing — this component exists only for its side effects.
  // The isOnline state is consumed by individual pages via the hook.
  return null;
}
