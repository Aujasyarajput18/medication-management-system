/**
 * Aujasya — usePillId Hook
 * Manages pill identification: model loading → camera → inference.
 * WebWorker + tf.disposeVariables() cleanup on unmount.
 */

'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import type { PillCandidate, PillIdStatus } from '@/types/pill-id.types';
import { PillWorkerManager } from '@/lib/ml/pill-worker';

export function usePillId() {
  const [status, setStatus] = useState<PillIdStatus>('idle');
  const [candidates, setCandidates] = useState<PillCandidate[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [modelProgress, setModelProgress] = useState(0);
  const workerRef = useRef<PillWorkerManager | null>(null);

  // Initialize and cleanup WebWorker
  useEffect(() => {
    const worker = new PillWorkerManager((loaded, total) => {
      setModelProgress(total > 0 ? loaded / total : 0);
    });
    workerRef.current = worker;

    return () => {
      // CRITICAL: dispose TF.js variables + terminate worker
      worker.dispose();
      workerRef.current = null;
    };
  }, []);

  const loadModel = useCallback(async () => {
    if (!workerRef.current) return;
    try {
      setStatus('loading_model');
      await workerRef.current.init();
      setStatus('idle');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Model load failed');
      setStatus('error');
    }
  }, []);

  const identifyPill = useCallback(async (imageData: ImageData) => {
    if (!workerRef.current) return;
    try {
      setStatus('identifying');
      setError(null);
      const results = await workerRef.current.identify(imageData);
      setCandidates(results);
      setStatus('done');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Identification failed');
      setStatus('error');
    }
  }, []);

  const reset = useCallback(() => {
    setStatus('idle');
    setCandidates([]);
    setError(null);
  }, []);

  return { status, candidates, error, modelProgress, loadModel, identifyPill, reset };
}
