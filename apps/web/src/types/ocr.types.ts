/** Aujasya — OCR Type Definitions */

export interface OcrEntityResult {
  text: string;
  label: 'DRUG' | 'DOSE' | 'FREQ' | 'DURATION' | 'DOCTOR';
  confidence: number;
}

export interface PrescriptionEntities {
  drugName: string | null;
  dosage: string | null;
  frequency: string | null;
  duration: string | null;
  prescribedBy: string | null;
  instructions: string | null;
  matchedMedicineId?: string | null;
  matchConfidence?: number | null;
}

export interface OcrResult {
  rawText: string;
  confidence: number;
  source: 'tesseract' | 'llava';
  entities: PrescriptionEntities;
  confidenceFlag?: 'low';
  userWarning?: string;
}

export type OcrStatus = 'idle' | 'preprocessing' | 'recognizing' | 'parsing' | 'done' | 'error';
