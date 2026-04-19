/**
 * Aujasya — Utility Tests
 */

import { describe, it, expect } from 'vitest';
import { getTimeOfDay, getCurrentMonthKey } from '@/lib/date-utils';

describe('Date Utilities', () => {
  it('should return valid time of day', () => {
    const result = getTimeOfDay();
    expect(['morning', 'afternoon', 'evening']).toContain(result);
  });

  it('should return current month key in YYYY-MM format', () => {
    const result = getCurrentMonthKey();
    expect(result).toMatch(/^\d{4}-\d{2}$/);
  });
});

describe('cn utility', () => {
  it('should merge class names', async () => {
    const { cn } = await import('@/lib/utils');
    expect(cn('foo', 'bar')).toBe('foo bar');
  });

  it('should handle conditional classes', async () => {
    const { cn } = await import('@/lib/utils');
    expect(cn('base', false && 'hidden', 'extra')).toBe('base extra');
  });

  it('should handle tailwind conflicts', async () => {
    const { cn } = await import('@/lib/utils');
    const result = cn('px-4', 'px-6');
    expect(result).toBe('px-6');
  });
});
