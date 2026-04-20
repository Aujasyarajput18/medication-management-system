/**
 * Aujasya — useDrugInteractions Hook
 * Checks drug interactions for a patient's active medications.
 * Results are informational — NEVER block user actions ("Add Anyway" UX).
 */

'use client';

import { useState, useCallback } from 'react';
import type { InteractionCheckResult, InteractionStatus } from '@/types/interaction.types';

export function useDrugInteractions() {
  const [status, setStatus] = useState<InteractionStatus>('idle');
  const [result, setResult] = useState<InteractionCheckResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const checkInteractions = useCallback(async (
    rxcuiList: string[],
    patientId: string,
  ) => {
    if (rxcuiList.length < 2) {
      setResult({ interactions: [], criticalCount: 0, majorCount: 0 });
      setStatus('done');
      return;
    }

    try {
      setStatus('checking');
      setError(null);

      const resp = await fetch(`/api/bff/interactions/check?patient_id=${patientId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rxcui_list: rxcuiList }),
      });

      if (!resp.ok) throw new Error('Check failed');
      const data: InteractionCheckResult = await resp.json();
      setResult(data);
      setStatus('done');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Check failed');
      setStatus('error');
    }
  }, []);

  const resolveRxcui = useCallback(async (medicineName: string): Promise<string | null> => {
    try {
      const resp = await fetch(`/api/bff/interactions/medicine/${encodeURIComponent(medicineName)}/rxcui`);
      if (!resp.ok) return null;
      const data = await resp.json();
      return data.found ? data.rxcui : null;
    } catch {
      return null;
    }
  }, []);

  return { status, result, error, checkInteractions, resolveRxcui };
}
