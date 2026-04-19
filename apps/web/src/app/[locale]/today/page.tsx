'use client';

/**
 * Aujasya — Today Page
 * Main dashboard showing today's doses grouped by meal anchor.
 */

import { useEffect, useMemo } from 'react';
import { useTranslations } from 'next-intl';
import { useParams } from 'next/navigation';
import { useDoseStore } from '@/stores/dose-store';
import { useAuthStore } from '@/stores/auth-store';
import { useOnlineStatus } from '@/hooks/use-online-status';
import { DoseCard } from '@/components/dose-card';
import { BottomNav } from '@/components/bottom-nav';
import { getTimeOfDay } from '@/lib/date-utils';

// Meal anchor ordering for display
const MEAL_ORDER = [
  'on_waking',
  'before_breakfast', 'with_breakfast', 'after_breakfast',
  'before_lunch', 'with_lunch', 'after_lunch',
  'before_dinner', 'with_dinner', 'after_dinner',
  'at_bedtime',
  'any_time',
];

export default function TodayPage() {
  const t = useTranslations('today');
  const { locale } = useParams<{ locale: string }>();
  const user = useAuthStore((s) => s.user);
  const { todayDoses, streak, isLoading, isOffline, fetchTodayDoses, fetchStreak } = useDoseStore();
  const isOnline = useOnlineStatus();

  useEffect(() => {
    fetchTodayDoses();
    fetchStreak();
  }, [fetchTodayDoses, fetchStreak]);

  // Group doses by meal anchor
  const groupedDoses = useMemo(() => {
    const groups: Record<string, typeof todayDoses> = {};
    for (const dose of todayDoses) {
      if (!groups[dose.mealAnchor]) groups[dose.mealAnchor] = [];
      groups[dose.mealAnchor].push(dose);
    }
    // Sort groups by MEAL_ORDER
    return MEAL_ORDER
      .filter((anchor) => groups[anchor])
      .map((anchor) => ({ anchor, doses: groups[anchor] }));
  }, [todayDoses]);

  const pendingCount = todayDoses.filter((d) => d.status === 'pending').length;
  const takenCount = todayDoses.filter((d) => d.status === 'taken').length;
  const totalCount = todayDoses.length;
  const progressPct = totalCount > 0 ? Math.round((takenCount / totalCount) * 100) : 0;
  const timeOfDay = getTimeOfDay();

  return (
    <div className="min-h-screen bg-background pb-24">
      {/* Header */}
      <header className="bg-gradient-to-br from-primary/10 via-background to-primary/5 px-4 pb-6 pt-safe">
        <div className="pt-4">
          {/* Offline banner */}
          {(isOffline || !isOnline) && (
            <div className="mb-3 flex items-center gap-2 rounded-lg bg-amber-100 px-3 py-2 text-sm text-amber-800 dark:bg-amber-900/30 dark:text-amber-200">
              <span>📡</span>
              <span>{t('noDoses') === '' ? 'Offline mode' : '📡 Offline'}</span>
            </div>
          )}

          <h1 className="text-2xl font-bold text-foreground">
            {t('greeting', {
              timeOfDay: t(timeOfDay),
              name: user?.fullName || '',
            })}
          </h1>

          {/* Progress ring / summary */}
          <div className="mt-4 flex items-center gap-6">
            {/* Circular progress */}
            <div className="relative h-20 w-20">
              <svg className="h-20 w-20 -rotate-90" viewBox="0 0 36 36">
                <circle
                  cx="18" cy="18" r="16"
                  className="fill-none stroke-muted"
                  strokeWidth="3"
                />
                <circle
                  cx="18" cy="18" r="16"
                  className="fill-none stroke-primary transition-all duration-700"
                  strokeWidth="3"
                  strokeDasharray={`${progressPct} 100`}
                  strokeLinecap="round"
                />
              </svg>
              <div className="absolute inset-0 flex items-center justify-center">
                <span className="text-lg font-bold text-foreground">{progressPct}%</span>
              </div>
            </div>

            <div className="flex-1 space-y-1">
              {pendingCount > 0 ? (
                <p className="text-sm font-medium text-muted-foreground">
                  {t('pending', { count: pendingCount })}
                </p>
              ) : totalCount > 0 ? (
                <p className="text-sm font-medium text-green-600">{t('allDone')}</p>
              ) : (
                <p className="text-sm text-muted-foreground">{t('noDoses')}</p>
              )}

              {streak.currentStreak > 0 && (
                <p className="text-sm text-orange-500 font-medium">
                  {t('streak', { days: streak.currentStreak })}
                </p>
              )}

              {streak.adherence30d > 0 && (
                <p className="text-xs text-muted-foreground">
                  {t('adherence', { percent: streak.adherence30d })}
                </p>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Dose List */}
      <div className="px-4 pt-4">
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          </div>
        ) : groupedDoses.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <span className="text-6xl mb-4">💊</span>
            <p className="text-lg font-medium text-muted-foreground">{t('noDoses')}</p>
          </div>
        ) : (
          <div className="space-y-6">
            {groupedDoses.map(({ anchor, doses }) => (
              <div key={anchor}>
                <h2 className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                  {anchor.replace(/_/g, ' ')}
                </h2>
                <div className="space-y-3">
                  {doses.map((dose) => (
                    <DoseCard key={dose.id} dose={dose} locale={locale} />
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <BottomNav locale={locale} />
    </div>
  );
}
