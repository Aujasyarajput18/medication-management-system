/** Aujasya — Pill ID Type Definitions */

export interface PillCandidate {
  drugName: string;
  confidence: number;
  color?: string | null;
  shape?: string | null;
  imprint?: string | null;
  matchedMedicineId?: string | null;
}

export interface BarcodeResult {
  medicineName: string | null;
  manufacturer: string | null;
  dosage: string | null;
  batchNumber: string | null;
  expiryDate: string | null;
  found: boolean;
}

export type PillIdStatus = 'idle' | 'loading_model' | 'capturing' | 'identifying' | 'done' | 'error';
