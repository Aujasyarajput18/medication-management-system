/**
 * Aujasya — useFastingMode Hook
 * Manages fasting mode activation, prayer times, and schedule adjustments.
 */

'use client';

import { useState, useCallback } from 'react';
import type { FastingActivationResult, PrayerTimes, FastingType } from '@/types/fasting.types';

export function useFastingMode() {
  const [prayerTimes, setPrayerTimes] = useState<PrayerTimes | null>(null);
  const [activation, setActivation] = useState<FastingActivationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchPrayerTimes = useCallback(async (lat: number, lng: number) => {
    try {
      setLoading(true);
      const resp = await fetch(`/api/bff/fasting/prayer-times?latitude=${lat}&longitude=${lng}`);
      if (!resp.ok) throw new Error('Failed to fetch prayer times');
      const data: PrayerTimes = await resp.json();
      setPrayerTimes(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed');
    } finally {
      setLoading(false);
    }
  }, []);

  const activateFasting = useCallback(async (
    patientId: string,
    fastingType: FastingType,
    startDate: string,
    lat: number,
    lng: number,
    endDate?: string,
  ) => {
    try {
      setLoading(true);
      setError(null);

      const resp = await fetch(`/api/bff/fasting/activate?patient_id=${patientId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          fasting_type: fastingType,
          start_date: startDate,
          end_date: endDate || null,
          latitude: lat,
          longitude: lng,
          disclaimer_accepted: true,
        }),
      });

      if (!resp.ok) throw new Error('Activation failed');
      const data: FastingActivationResult = await resp.json();
      setActivation(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed');
    } finally {
      setLoading(false);
    }
  }, []);

  const reset = useCallback(() => {
    setActivation(null);
    setError(null);
  }, []);

  return { prayerTimes, activation, loading, error, fetchPrayerTimes, activateFasting, reset };
}
