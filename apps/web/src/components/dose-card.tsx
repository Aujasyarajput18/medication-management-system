'use client';

/**
 * Aujasya — Dose Card Component
 * Displays a single dose with swipe-to-take/skip and visual status indicators.
 */

import { useState } from 'react';
import { cn } from '@/lib/utils';
import { useDoseStore } from '@/stores/dose-store';
import { useSwipeAction } from '@/hooks/use-swipe-action';
import { useMealAnchorTime } from '@/hooks/use-meal-anchor-time';
import { useTranslations } from 'next-intl';

interface DoseCardProps {
  dose: {
    id: string;
    medicineName?: string;
    dosageValue?: number;
    dosageUnit?: string;
    medicineForm?: string;
    mealAnchor: string;
    status: string;
  };
  locale?: string;
}

export function DoseCard({ dose, locale = 'en' }: DoseCardProps) {
  const t = useTranslations('today');
  const markTaken = useDoseStore((s) => s.markTaken);
  const markSkipped = useDoseStore((s) => s.markSkipped);
  const { getDisplayName, getTimeForAnchor, formatTime12h } = useMealAnchorTime();
  const [showSkipModal, setShowSkipModal] = useState(false);
  const [skipReason, setSkipReason] = useState('');

  const { swipeHandlers, offsetX, swipeDirection } = useSwipeAction({
    threshold: 80,
    onSwipeRight: () => {
      if (dose.status === 'pending') markTaken(dose.id);
    },
    onSwipeLeft: () => {
      if (dose.status === 'pending') setShowSkipModal(true);
    },
  });

  const statusStyles: Record<string, string> = {
    pending: 'border-l-4 border-l-amber-400 bg-card',
    taken: 'border-l-4 border-l-green-500 bg-green-50 dark:bg-green-950/20',
    skipped: 'border-l-4 border-l-gray-400 bg-gray-50 dark:bg-gray-900/20 opacity-70',
    missed: 'border-l-4 border-l-red-500 bg-red-50 dark:bg-red-950/20',
  };

  const statusBadge: Record<string, { text: string; className: string }> = {
    taken: { text: `✅ ${t('taken')}`, className: 'text-green-600 bg-green-100 dark:bg-green-900/30' },
    skipped: { text: `⏭️ ${t('skipped')}`, className: 'text-gray-600 bg-gray-100 dark:bg-gray-800' },
    missed: { text: `❌ ${t('missed')}`, className: 'text-red-600 bg-red-100 dark:bg-red-900/30' },
  };

  const time = getTimeForAnchor(dose.mealAnchor);

  const handleSkipSubmit = () => {
    if (skipReason.length >= 5) {
      markSkipped(dose.id, skipReason);
      setShowSkipModal(false);
      setSkipReason('');
    }
  };

  return (
    <>
      <div
        {...swipeHandlers}
        className={cn(
          'relative overflow-hidden rounded-xl p-4 shadow-sm transition-all',
          statusStyles[dose.status] || statusStyles.pending,
          dose.status === 'pending' && 'active:scale-[0.98]'
        )}
        style={{
          transform: dose.status === 'pending' ? `translateX(${offsetX}px)` : undefined,
        }}
        role="article"
        aria-label={`${dose.medicineName} - ${dose.status}`}
      >
        {/* Swipe indicators */}
        {swipeDirection === 'right' && dose.status === 'pending' && (
          <div className="absolute inset-y-0 left-0 flex w-20 items-center justify-center bg-green-500 text-white text-2xl">
            ✅
          </div>
        )}
        {swipeDirection === 'left' && dose.status === 'pending' && (
          <div className="absolute inset-y-0 right-0 flex w-20 items-center justify-center bg-gray-500 text-white text-2xl">
            ⏭️
          </div>
        )}

        <div className="flex items-start justify-between">
          <div className="flex-1">
            <h3 className="font-semibold text-foreground">
              {dose.medicineName || 'Medicine'}
            </h3>
            <p className="text-sm text-muted-foreground">
              {dose.dosageValue} {dose.dosageUnit} · {dose.medicineForm}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              {getDisplayName(dose.mealAnchor, locale)}
              {time && ` · ${formatTime12h(time)}`}
            </p>
          </div>

          <div className="flex flex-col items-end gap-2">
            {dose.status !== 'pending' && statusBadge[dose.status] && (
              <span
                className={cn(
                  'rounded-full px-2.5 py-1 text-xs font-medium',
                  statusBadge[dose.status].className
                )}
              >
                {statusBadge[dose.status].text}
              </span>
            )}

            {dose.status === 'pending' && (
              <div className="flex gap-2">
                <button
                  onClick={() => markTaken(dose.id)}
                  className="min-h-touch min-w-touch rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow-sm transition-colors hover:bg-primary/90 active:scale-95"
                  aria-label={`${t('markTaken')} ${dose.medicineName}`}
                >
                  {t('markTaken')}
                </button>
                <button
                  onClick={() => setShowSkipModal(true)}
                  className="min-h-touch rounded-lg border border-border px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-muted"
                  aria-label={`${t('markSkipped')} ${dose.medicineName}`}
                >
                  {t('markSkipped')}
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Skip Reason Modal */}
      {showSkipModal && (
        <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 sm:items-center">
          <div className="w-full max-w-md rounded-t-2xl bg-card p-6 shadow-xl sm:rounded-2xl">
            <h3 className="text-lg font-semibold">{t('skipReasonTitle')}</h3>
            <textarea
              value={skipReason}
              onChange={(e) => setSkipReason(e.target.value)}
              placeholder={t('skipReasonPlaceholder')}
              className="mt-3 w-full rounded-lg border border-input bg-background p-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              rows={3}
              autoFocus
            />
            <div className="mt-4 flex gap-3">
              <button
                onClick={() => setShowSkipModal(false)}
                className="flex-1 rounded-lg border border-border py-3 text-sm font-medium"
              >
                Cancel
              </button>
              <button
                onClick={handleSkipSubmit}
                disabled={skipReason.length < 5}
                className="flex-1 rounded-lg bg-primary py-3 text-sm font-medium text-primary-foreground disabled:opacity-50"
              >
                {t('markSkipped')}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
