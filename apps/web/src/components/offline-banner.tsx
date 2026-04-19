'use client';

/**
 * Aujasya — Offline Banner Component
 * Shown at top of pages when user is offline.
 */

import { useOnlineStatus } from '@/hooks/use-online-status';
import { useTranslations } from 'next-intl';

export function OfflineBanner() {
  const isOnline = useOnlineStatus();
  const t = useTranslations('common');

  if (isOnline) return null;

  return (
    <div
      className="fixed top-0 left-0 right-0 z-40 flex items-center justify-center gap-2 bg-amber-500 px-4 py-2 text-sm font-medium text-white shadow-md"
      role="alert"
    >
      <span>📡</span>
      <span>{t('offline')}</span>
      <span className="text-xs opacity-80">— {t('syncPending')}</span>
    </div>
  );
}
