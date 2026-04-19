/**
 * Aujasya — Medicine Store (Zustand)
 */

import { create } from 'zustand';
import api from '@/lib/api-client';

interface Schedule {
  id: string;
  medicineId: string;
  mealAnchor: string;
  offsetMinutes: number;
  doseQuantity: number;
  daysOfWeek: number[];
  isActive: boolean;
  effectiveFrom: string;
  effectiveUntil: string | null;
  reminderLevel: number;
}

interface Medicine {
  id: string;
  patientId: string;
  brandName: string;
  genericName: string | null;
  dosageValue: number;
  dosageUnit: string;
  form: string;
  isActive: boolean;
  startDate: string;
  endDate: string | null;
  prescribedBy: string | null;
  instructions: string | null;
  totalQuantity: number | null;
  remainingQuantity: number | null;
  schedules: Schedule[];
  createdAt: string;
}

interface MedicineState {
  medicines: Medicine[];
  isLoading: boolean;

  fetchMedicines: () => Promise<void>;
  addMedicine: (data: any) => Promise<Medicine>;
  updateMedicine: (id: string, data: any) => Promise<void>;
  deactivateMedicine: (id: string) => Promise<void>;
}

function transformMedicine(raw: any): Medicine {
  return {
    id: raw.id,
    patientId: raw.patient_id,
    brandName: raw.brand_name,
    genericName: raw.generic_name,
    dosageValue: raw.dosage_value,
    dosageUnit: raw.dosage_unit,
    form: raw.form,
    isActive: raw.is_active,
    startDate: raw.start_date,
    endDate: raw.end_date,
    prescribedBy: raw.prescribed_by,
    instructions: raw.instructions,
    totalQuantity: raw.total_quantity,
    remainingQuantity: raw.remaining_quantity,
    schedules: (raw.schedules || []).map((s: any) => ({
      id: s.id,
      medicineId: s.medicine_id,
      mealAnchor: s.meal_anchor,
      offsetMinutes: s.offset_minutes,
      doseQuantity: s.dose_quantity,
      daysOfWeek: s.days_of_week,
      isActive: s.is_active,
      effectiveFrom: s.effective_from,
      effectiveUntil: s.effective_until,
      reminderLevel: s.reminder_level,
    })),
    createdAt: raw.created_at,
  };
}

export const useMedicineStore = create<MedicineState>((set) => ({
  medicines: [],
  isLoading: false,

  fetchMedicines: async () => {
    set({ isLoading: true });
    try {
      const { data } = await api.get('/medicines');
      set({ medicines: data.map(transformMedicine), isLoading: false });
    } catch {
      set({ isLoading: false });
    }
  },

  addMedicine: async (formData: any) => {
    const { data } = await api.post('/medicines', formData);
    const medicine = transformMedicine(data);
    set((state) => ({ medicines: [medicine, ...state.medicines] }));
    return medicine;
  },

  updateMedicine: async (id: string, updateData: any) => {
    const { data } = await api.patch(`/medicines/${id}`, updateData);
    const updated = transformMedicine(data);
    set((state) => ({
      medicines: state.medicines.map((m) => (m.id === id ? updated : m)),
    }));
  },

  deactivateMedicine: async (id: string) => {
    await api.delete(`/medicines/${id}`);
    set((state) => ({
      medicines: state.medicines.filter((m) => m.id !== id),
    }));
  },
}));
