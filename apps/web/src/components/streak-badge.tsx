'use client';

/**
 * Aujasya — Streak Badge Component
 * Animated streak counter shown on the Today page.
 */

interface StreakBadgeProps {
  currentStreak: number;
  adherence30d: number;
}

export function StreakBadge({ currentStreak, adherence30d }: StreakBadgeProps) {
  if (currentStreak === 0 && adherence30d === 0) return null;

  return (
    <div className="flex items-center gap-3">
      {currentStreak > 0 && (
        <div className="flex items-center gap-1.5 rounded-full bg-orange-100 px-3 py-1.5 dark:bg-orange-900/30">
          <span className="text-base">🔥</span>
          <span className="text-sm font-bold text-orange-600 dark:text-orange-400">
            {currentStreak}
          </span>
        </div>
      )}
      {adherence30d > 0 && (
        <div className="flex items-center gap-1.5 rounded-full bg-blue-100 px-3 py-1.5 dark:bg-blue-900/30">
          <span className="text-base">📊</span>
          <span className="text-sm font-medium text-blue-600 dark:text-blue-400">
            {adherence30d}%
          </span>
        </div>
      )}
    </div>
  );
}
