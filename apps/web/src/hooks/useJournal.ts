/**
 * Aujasya — useJournal Hook
 * Manages side-effect journal entry creation and pattern detection.
 */

'use client';

import { useState, useCallback } from 'react';
import type {
  JournalEntry,
  JournalPatternsResult,
  JournalStatus,
} from '@/types/journal.types';

export function useJournal() {
  const [status, setStatus] = useState<JournalStatus>('idle');
  const [entries, setEntries] = useState<JournalEntry[]>([]);
  const [patterns, setPatterns] = useState<JournalPatternsResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const createEntry = useCallback(
    async (
      patientId: string,
      data: {
        symptomText: string;
        severity: 'mild' | 'moderate' | 'severe';
        onsetDate: string;
        inputMethod: 'voice' | 'text';
        medicineId?: string;
        doseLogId?: string;
        voiceTranscript?: string;
      }
    ) => {
      try {
        setStatus('saving');
        setError(null);

        const resp = await fetch(
          `/api/bff/journal/entry?patient_id=${patientId}`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              symptom_text: data.symptomText,
              severity: data.severity,
              onset_date: data.onsetDate,
              input_method: data.inputMethod,
              medicine_id: data.medicineId || null,
              dose_log_id: data.doseLogId || null,
              voice_transcript: data.voiceTranscript || null,
            }),
          }
        );

        if (!resp.ok) throw new Error('Failed to save journal entry');

        const entry: JournalEntry = await resp.json();
        setEntries((prev) => [entry, ...prev]);
        setStatus('done');
        return entry;
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Save failed');
        setStatus('error');
        return null;
      }
    },
    []
  );

  const fetchPatterns = useCallback(
    async (patientId: string, periodDays = 30) => {
      try {
        setStatus('loading');
        setError(null);

        const resp = await fetch(
          `/api/bff/journal/patterns?patient_id=${patientId}&period_days=${periodDays}`
        );
        if (!resp.ok) throw new Error('Failed to fetch patterns');

        const data: JournalPatternsResult = await resp.json();
        setPatterns(data);
        setStatus('done');
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Fetch failed');
        setStatus('error');
      }
    },
    []
  );

  const reset = useCallback(() => {
    setStatus('idle');
    setError(null);
  }, []);

  return {
    status,
    entries,
    patterns,
    error,
    createEntry,
    fetchPatterns,
    reset,
  };
}
