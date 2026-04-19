/**
 * Aujasya — Dose Store Tests
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useDoseStore } from '@/stores/dose-store';

vi.mock('@/lib/api-client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

vi.mock('@/lib/offline-db', () => ({
  addToSyncQueue: vi.fn().mockResolvedValue('sync-1'),
  cacheDoses: vi.fn().mockResolvedValue(undefined),
  getCachedDosesByDate: vi.fn().mockResolvedValue([]),
  updateCachedDoseStatus: vi.fn().mockResolvedValue(undefined),
  getPendingSyncItems: vi.fn().mockResolvedValue([]),
  markSynced: vi.fn().mockResolvedValue(undefined),
}));

describe('Dose Store', () => {
  beforeEach(() => {
    useDoseStore.setState({
      todayDoses: [],
      streak: { currentStreak: 0, longestStreak: 0, adherence30d: 0 },
      isLoading: false,
      isOffline: false,
    });
  });

  it('should have initial state', () => {
    const state = useDoseStore.getState();
    expect(state.todayDoses).toEqual([]);
    expect(state.isLoading).toBe(false);
    expect(state.isOffline).toBe(false);
  });

  it('should optimistically mark dose as taken', async () => {
    useDoseStore.setState({
      todayDoses: [
        {
          id: 'dose-1',
          scheduleId: 's1',
          medicineId: 'm1',
          patientId: 'p1',
          scheduledDate: '2025-01-15',
          mealAnchor: 'after_breakfast',
          status: 'pending',
          loggedAt: null,
          skipReason: null,
          notes: null,
        },
      ],
    });

    const api = (await import('@/lib/api-client')).default;
    (api.post as any).mockResolvedValueOnce({ data: {} });

    await useDoseStore.getState().markTaken('dose-1');

    const state = useDoseStore.getState();
    expect(state.todayDoses[0].status).toBe('taken');
    expect(state.todayDoses[0].loggedAt).toBeTruthy();
  });

  it('should queue offline when API fails', async () => {
    useDoseStore.setState({
      todayDoses: [
        {
          id: 'dose-2',
          scheduleId: 's1',
          medicineId: 'm1',
          patientId: 'p1',
          scheduledDate: '2025-01-15',
          mealAnchor: 'after_lunch',
          status: 'pending',
          loggedAt: null,
          skipReason: null,
          notes: null,
        },
      ],
    });

    const api = (await import('@/lib/api-client')).default;
    (api.post as any).mockRejectedValueOnce(new Error('Network error'));

    const { addToSyncQueue } = await import('@/lib/offline-db');

    await useDoseStore.getState().markTaken('dose-2');

    // Still optimistically updated
    expect(useDoseStore.getState().todayDoses[0].status).toBe('taken');
    // Queued for offline sync
    expect(addToSyncQueue).toHaveBeenCalled();
  });

  it('should optimistically mark dose as skipped', async () => {
    useDoseStore.setState({
      todayDoses: [
        {
          id: 'dose-3',
          scheduleId: 's1',
          medicineId: 'm1',
          patientId: 'p1',
          scheduledDate: '2025-01-15',
          mealAnchor: 'after_dinner',
          status: 'pending',
          loggedAt: null,
          skipReason: null,
          notes: null,
        },
      ],
    });

    const api = (await import('@/lib/api-client')).default;
    (api.post as any).mockResolvedValueOnce({ data: {} });

    await useDoseStore.getState().markSkipped('dose-3', 'Feeling nauseous');

    const state = useDoseStore.getState();
    expect(state.todayDoses[0].status).toBe('skipped');
    expect(state.todayDoses[0].skipReason).toBe('Feeling nauseous');
  });
});
