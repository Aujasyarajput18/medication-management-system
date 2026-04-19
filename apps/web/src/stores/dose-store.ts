/**
 * Aujasya — Dose Store (Zustand)
 * Manages today's doses, optimistic UI updates, and offline queue.
 */

import { create } from 'zustand';
import api from '@/lib/api-client';
import {
  addToSyncQueue,
  cacheDoses,
  getCachedDosesByDate,
  updateCachedDoseStatus,
} from '@/lib/offline-db';

interface DoseLog {
  id: string;
  scheduleId: string;
  medicineId: string;
  patientId: string;
  scheduledDate: string;
  mealAnchor: string;
  status: 'pending' | 'taken' | 'skipped' | 'missed';
  loggedAt: string | null;
  skipReason: string | null;
  notes: string | null;
  medicineName?: string;
  dosageValue?: number;
  dosageUnit?: string;
  medicineForm?: string;
}

interface Streak {
  currentStreak: number;
  longestStreak: number;
  adherence30d: number;
}

interface DoseState {
  todayDoses: DoseLog[];
  streak: Streak;
  isLoading: boolean;
  isOffline: boolean;

  // Actions
  fetchTodayDoses: () => Promise<void>;
  markTaken: (doseId: string, notes?: string) => Promise<void>;
  markSkipped: (doseId: string, reason: string) => Promise<void>;
  fetchStreak: () => Promise<void>;
  syncOffline: () => Promise<void>;
}

export const useDoseStore = create<DoseState>((set, get) => ({
  todayDoses: [],
  streak: { currentStreak: 0, longestStreak: 0, adherence30d: 0 },
  isLoading: false,
  isOffline: false,

  fetchTodayDoses: async () => {
    set({ isLoading: true });
    try {
      const { data } = await api.get('/doses/today');
      const doses: DoseLog[] = data.map((d: any) => ({
        id: d.id,
        scheduleId: d.schedule_id,
        medicineId: d.medicine_id,
        patientId: d.patient_id,
        scheduledDate: d.scheduled_date,
        mealAnchor: d.meal_anchor,
        status: d.status,
        loggedAt: d.logged_at,
        skipReason: d.skip_reason,
        notes: d.notes,
        medicineName: d.medicine_name,
        dosageValue: d.dosage_value,
        dosageUnit: d.dosage_unit,
        medicineForm: d.medicine_form,
      }));
      set({ todayDoses: doses, isLoading: false, isOffline: false });

      // Cache for offline use
      await cacheDoses(
        doses.map((d) => ({
          id: d.id,
          scheduleId: d.scheduleId,
          medicineId: d.medicineId,
          scheduledDate: d.scheduledDate,
          mealAnchor: d.mealAnchor,
          status: d.status,
          medicineName: d.medicineName,
          dosageValue: d.dosageValue,
          dosageUnit: d.dosageUnit,
          cachedAt: new Date().toISOString(),
        }))
      );
    } catch (error) {
      // Fall back to cached doses
      const today = new Date().toISOString().split('T')[0];
      const cached = await getCachedDosesByDate(today);
      if (cached.length > 0) {
        set({
          todayDoses: cached.map((c) => ({
            id: c.id,
            scheduleId: c.scheduleId,
            medicineId: c.medicineId,
            patientId: '',
            scheduledDate: c.scheduledDate,
            mealAnchor: c.mealAnchor,
            status: c.status as DoseLog['status'],
            loggedAt: null,
            skipReason: null,
            notes: null,
            medicineName: c.medicineName,
            dosageValue: c.dosageValue,
            dosageUnit: c.dosageUnit,
          })),
          isLoading: false,
          isOffline: true,
        });
      } else {
        set({ isLoading: false, isOffline: true });
      }
    }
  },

  markTaken: async (doseId: string, notes?: string) => {
    // Optimistic update
    set((state) => ({
      todayDoses: state.todayDoses.map((d) =>
        d.id === doseId
          ? { ...d, status: 'taken' as const, loggedAt: new Date().toISOString() }
          : d
      ),
    }));

    try {
      await api.post(`/doses/${doseId}/taken`, { notes });
      await updateCachedDoseStatus(doseId, 'taken');
    } catch {
      // Queue for offline sync
      await addToSyncQueue({
        doseId,
        action: 'taken',
        deviceTimestamp: new Date().toISOString(),
        notes,
      });
    }
  },

  markSkipped: async (doseId: string, reason: string) => {
    set((state) => ({
      todayDoses: state.todayDoses.map((d) =>
        d.id === doseId
          ? { ...d, status: 'skipped' as const, skipReason: reason }
          : d
      ),
    }));

    try {
      await api.post(`/doses/${doseId}/skipped`, { skip_reason: reason });
      await updateCachedDoseStatus(doseId, 'skipped');
    } catch {
      await addToSyncQueue({
        doseId,
        action: 'skipped',
        deviceTimestamp: new Date().toISOString(),
        skipReason: reason,
      });
    }
  },

  fetchStreak: async () => {
    try {
      const { data } = await api.get('/doses/streak');
      set({
        streak: {
          currentStreak: data.current_streak,
          longestStreak: data.longest_streak,
          adherence30d: data.adherence_30d,
        },
      });
    } catch {
      /* offline — use cached */
    }
  },

  syncOffline: async () => {
    const { getPendingSyncItems, markSynced } = await import('@/lib/offline-db');
    const pending = await getPendingSyncItems();
    if (pending.length === 0) return;

    try {
      const { data } = await api.post('/doses/sync-offline', {
        mutations: pending.map((p) => ({
          dose_id: p.doseId,
          action: p.action,
          device_timestamp: p.deviceTimestamp,
          notes: p.notes,
          skip_reason: p.skipReason,
        })),
      });

      // Mark synced items
      for (const item of pending) {
        await markSynced(item.id);
      }
    } catch {
      /* Will retry next time */
    }
  },
}));
