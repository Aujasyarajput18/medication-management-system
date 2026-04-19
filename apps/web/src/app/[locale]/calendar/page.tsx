'use client';

/**
 * Aujasya — Calendar Page
 * Monthly adherence calendar with color-coded days.
 * [FIX-15] Uses month=YYYY-MM query param.
 */

import { useState, useEffect } from 'react';
import { useTranslations } from 'next-intl';
import { useParams } from 'next/navigation';
import api from '@/lib/api-client';
import { BottomNav } from '@/components/bottom-nav';
import { getCurrentMonthKey } from '@/lib/date-utils';
import { cn } from '@/lib/utils';

interface DayData {
  date: string;
  total: number;
  taken: number;
  missed: number;
  skipped: number;
  adherence_pct: number;
}

export default function CalendarPage() {
  const t = useTranslations('calendar');
  const { locale } = useParams<{ locale: string }>();
  const [month, setMonth] = useState(getCurrentMonthKey());
  const [days, setDays] = useState<DayData[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchCalendar = async () => {
      setIsLoading(true);
      try {
        const { data } = await api.get('/doses/calendar', { params: { month } });
        setDays(data.days || []);
      } catch {
        setDays([]);
      }
      setIsLoading(false);
    };
    fetchCalendar();
  }, [month]);

  const [year, monthNum] = month.split('-').map(Number);
  const firstDay = new Date(year, monthNum - 1, 1).getDay();
  const daysInMonth = new Date(year, monthNum, 0).getDate();

  const goToPrevMonth = () => {
    const d = new Date(year, monthNum - 2, 1);
    setMonth(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`);
  };

  const goToNextMonth = () => {
    const d = new Date(year, monthNum, 1);
    setMonth(`${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`);
  };

  const dayMap = new Map(days.map((d) => [d.date, d]));

  const getDayColor = (date: string): string => {
    const data = dayMap.get(date);
    if (!data || data.total === 0) return 'bg-muted text-muted-foreground';
    if (data.adherence_pct >= 100) return 'bg-green-500 text-white';
    if (data.adherence_pct >= 80) return 'bg-green-300 text-green-900';
    if (data.adherence_pct >= 50) return 'bg-amber-300 text-amber-900';
    return 'bg-red-300 text-red-900';
  };

  const weekDays = ['S', 'M', 'T', 'W', 'T', 'F', 'S'];
  const monthNames = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December',
  ];

  return (
    <div className="min-h-screen bg-background pb-24">
      <header className="border-b border-border bg-card px-4 pb-4 pt-safe">
        <h1 className="pt-4 text-2xl font-bold">{t('title')}</h1>
      </header>

      <div className="px-4 pt-4">
        {/* Month selector */}
        <div className="flex items-center justify-between mb-4">
          <button onClick={goToPrevMonth} className="rounded-lg p-2 hover:bg-muted" aria-label="Previous month">
            ◀
          </button>
          <h2 className="text-lg font-semibold">
            {monthNames[monthNum - 1]} {year}
          </h2>
          <button onClick={goToNextMonth} className="rounded-lg p-2 hover:bg-muted" aria-label="Next month">
            ▶
          </button>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          </div>
        ) : (
          <>
            {/* Calendar grid */}
            <div className="grid grid-cols-7 gap-1">
              {weekDays.map((day) => (
                <div key={day} className="py-2 text-center text-xs font-medium text-muted-foreground">
                  {day}
                </div>
              ))}
              {/* Empty cells for offset */}
              {Array.from({ length: firstDay }).map((_, i) => (
                <div key={`empty-${i}`} />
              ))}
              {/* Day cells */}
              {Array.from({ length: daysInMonth }).map((_, i) => {
                const dayNum = i + 1;
                const dateStr = `${year}-${String(monthNum).padStart(2, '0')}-${String(dayNum).padStart(2, '0')}`;
                return (
                  <div
                    key={dateStr}
                    className={cn(
                      'flex h-10 items-center justify-center rounded-lg text-sm font-medium transition-colors',
                      getDayColor(dateStr)
                    )}
                    title={`${dateStr}: ${dayMap.get(dateStr)?.adherence_pct ?? 0}%`}
                  >
                    {dayNum}
                  </div>
                );
              })}
            </div>

            {/* Legend */}
            <div className="mt-6 flex flex-wrap gap-4 text-xs">
              <div className="flex items-center gap-1.5">
                <div className="h-3 w-3 rounded bg-green-500" />
                <span>{t('perfect')}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="h-3 w-3 rounded bg-green-300" />
                <span>{t('good')}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="h-3 w-3 rounded bg-red-300" />
                <span>{t('poor')}</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="h-3 w-3 rounded bg-muted" />
                <span>{t('noData')}</span>
              </div>
            </div>
          </>
        )}
      </div>

      <BottomNav locale={locale} />
    </div>
  );
}
