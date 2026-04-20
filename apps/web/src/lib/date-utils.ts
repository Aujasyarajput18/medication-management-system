/**
 * Aujasya — Date Formatting Utilities
 * IST-aware date formatting for Indian users.
 */

import { format, formatDistanceToNow, isToday, isYesterday, parseISO } from 'date-fns';
import type { Locale } from 'date-fns';
import { hi, enIN, ta, te, bn } from 'date-fns/locale';

const LOCALE_MAP: Record<string, Locale> = {
  hi: hi,
  en: enIN,
  ta: ta,
  te: te,
  bn: bn,
  mr: enIN,
};

export function formatDate(dateStr: string, locale: string = 'en'): string {
  const date = parseISO(dateStr);
  const dateLocale = LOCALE_MAP[locale] || enIN;

  if (isToday(date)) return 'Today';
  if (isYesterday(date)) return 'Yesterday';

  return format(date, 'dd MMM yyyy', { locale: dateLocale });
}

export function formatTime(dateStr: string): string {
  return format(parseISO(dateStr), 'hh:mm a');
}

export function formatRelative(dateStr: string, locale: string = 'en'): string {
  const dateLocale = LOCALE_MAP[locale] || enIN;
  return formatDistanceToNow(parseISO(dateStr), {
    addSuffix: true,
    locale: dateLocale,
  });
}

export function getTimeOfDay(): 'morning' | 'afternoon' | 'evening' {
  const hour = new Date().getHours();
  if (hour < 12) return 'morning';
  if (hour < 17) return 'afternoon';
  return 'evening';
}

export function getCurrentMonthKey(): string {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
}
