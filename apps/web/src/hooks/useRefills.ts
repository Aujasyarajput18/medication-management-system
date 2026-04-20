/**
 * Aujasya — useRefills Hook
 * Manages refill status and remaining quantity updates.
 */

'use client';

import { useState, useCallback } from 'react';
import type { RefillStatus, RefillViewStatus } from '@/types/refill.types';

export function useRefills() {
  const [status, setStatus] = useState<RefillViewStatus>('idle');
  const [refills, setRefills] = useState<RefillStatus[]>([]);
  const [error, setError] = useState<string | null>(null);

  const fetchRefills = useCallback(
    async (patientId: string, lat?: number, lng?: number) => {
      try {
        setStatus('loading');
        setError(null);

        const params = new URLSearchParams({ patient_id: patientId });
        if (lat !== undefined) params.set('latitude', lat.toString());
        if (lng !== undefined) params.set('longitude', lng.toString());

        const resp = await fetch(`/api/bff/refills/status?${params}`);
        if (!resp.ok) throw new Error('Failed to fetch refill status');

        const data: RefillStatus[] = await resp.json();
        setRefills(data);
        setStatus('done');
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Fetch failed');
        setStatus('error');
      }
    },
    []
  );

  const updateCount = useCallback(
    async (medicineId: string, remaining: number) => {
      try {
        const resp = await fetch(`/api/bff/refills/${medicineId}/count`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            remaining_quantity: remaining,
            update_source: 'manual',
          }),
        });
        if (!resp.ok) throw new Error('Update failed');

        // Update local state
        setRefills((prev) =>
          prev.map((r) =>
            r.medicineId === medicineId
              ? { ...r, remainingQuantity: remaining }
              : r
          )
        );
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Update failed');
      }
    },
    []
  );

  return { status, refills, error, fetchRefills, updateCount };
}
