/** Aujasya — Refill Tracking Type Definitions */

export interface JanAushadhiKendra {
  name: string;
  address: string;
  distanceKm: number;
  lat: number;
  lng: number;
}

export interface RefillStatus {
  medicineId: string;
  brandName: string;
  remainingQuantity: number | null;
  dailyDoseCount: number;
  daysRemaining: number | null;
  projectedRunoutDate: string | null;
  alertRequired: boolean;
  nearestKendras: JanAushadhiKendra[];
}

export type RefillViewStatus = 'idle' | 'loading' | 'done' | 'error';
