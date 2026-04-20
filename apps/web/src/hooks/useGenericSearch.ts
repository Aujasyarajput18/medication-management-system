/**
 * Aujasya — useGenericSearch Hook
 * Searches for generic drug alternatives with caching.
 */

'use client';

import { useState, useCallback } from 'react';
import type { GenericSearchResult, GenericSearchStatus } from '@/types/generic.types';

export function useGenericSearch() {
  const [status, setStatus] = useState<GenericSearchStatus>('idle');
  const [result, setResult] = useState<GenericSearchResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const searchGenerics = useCallback(async (
    brandName: string,
    patientId: string,
    lat?: number,
    lng?: number,
  ) => {
    try {
      setStatus('searching');
      setError(null);

      const params = new URLSearchParams({
        brand_name: brandName,
        patient_id: patientId,
      });
      if (lat !== undefined) params.set('latitude', lat.toString());
      if (lng !== undefined) params.set('longitude', lng.toString());

      const resp = await fetch(`/api/bff/generics/search?${params}`);
      if (!resp.ok) throw new Error('Search failed');

      const data = await resp.json();
      setResult(data);
      setStatus('done');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Search failed');
      setStatus('error');
    }
  }, []);

  const reset = useCallback(() => {
    setStatus('idle');
    setResult(null);
    setError(null);
  }, []);

  return { status, result, error, searchGenerics, reset };
}
