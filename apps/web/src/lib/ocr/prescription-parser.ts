/**
 * Aujasya — Client-side Prescription Parser
 * Regex + rule-based entity extraction from OCR text.
 * Mirrors server-side PrescriptionParserService for offline use.
 */

export interface PrescriptionEntities {
  drugName: string | null;
  dosage: string | null;
  frequency: string | null;
  duration: string | null;
  prescribedBy: string | null;
  instructions: string | null;
}

const FREQUENCY_MAP: Record<string, string> = {
  '1-0-1': 'morning-night',
  '1-1-1': 'morning-afternoon-night',
  '0-0-1': 'night-only',
  '1-0-0': 'morning-only',
  '0-1-0': 'afternoon-only',
  '1-1-0': 'morning-afternoon',
};

const DOSAGE_RE = /(\d+(?:\.\d+)?)\s*(mg|mcg|ml|g|IU|units?)/i;
const DURATION_RE = /(\d+)\s*(days?|weeks?|months?)/i;
const DOCTOR_RE = /(?:Dr\.?|Doctor)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)/i;
const FREQ_PATTERN_RE = /\b(\d)\s*[-–]\s*(\d)\s*[-–]\s*(\d)\b/;

export function parsePrescription(rawText: string): PrescriptionEntities {
  const entities: PrescriptionEntities = {
    drugName: null,
    dosage: null,
    frequency: null,
    duration: null,
    prescribedBy: null,
    instructions: null,
  };

  // Extract dosage
  const dosageMatch = rawText.match(DOSAGE_RE);
  if (dosageMatch) {
    entities.dosage = dosageMatch[0];
  }

  // Extract frequency (1-0-1 pattern)
  const freqMatch = rawText.match(FREQ_PATTERN_RE);
  if (freqMatch) {
    const key = `${freqMatch[1]}-${freqMatch[2]}-${freqMatch[3]}`;
    entities.frequency = FREQUENCY_MAP[key] || key;
  } else {
    // Check abbreviations
    const abbrevs = ['OD', 'BD', 'TDS', 'QID', 'SOS', 'HS'];
    for (const abbr of abbrevs) {
      if (new RegExp(`\\b${abbr}\\b`, 'i').test(rawText)) {
        entities.frequency = abbr.toLowerCase();
        break;
      }
    }
  }

  // Extract duration
  const durMatch = rawText.match(DURATION_RE);
  if (durMatch) {
    entities.duration = durMatch[0];
  }

  // Extract doctor
  const docMatch = rawText.match(DOCTOR_RE);
  if (docMatch) {
    entities.prescribedBy = docMatch[1];
  }

  // Extract meal instructions
  if (/\b(?:after|with)\s+(?:food|meal)\b/i.test(rawText)) {
    entities.instructions = 'after food';
  } else if (/\b(?:before|empty)\s+(?:food|meal|stomach)\b/i.test(rawText)) {
    entities.instructions = 'before food';
  }

  return entities;
}
