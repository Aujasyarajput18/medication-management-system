/** Aujasya — Side-Effect Journal Type Definitions */

export interface JournalEntry {
  id: string;
  medicineId: string | null;
  symptomText: string;
  symptomNormalized: string[];
  severity: 'mild' | 'moderate' | 'severe';
  onsetDate: string;
  resolvedDate: string | null;
  inputMethod: 'voice' | 'text';
  isFlagged: boolean;
  flagReason: string | null;
  createdAt: string;
}

export interface SymptomPattern {
  symptom: string;
  count: number;
  medicineName: string | null;
  firstOccurrence: string;
  lastOccurrence: string;
}

export interface JournalPatternsResult {
  patterns: SymptomPattern[];
  periodDays: number;
}

export type JournalStatus = 'idle' | 'saving' | 'loading' | 'done' | 'error';
