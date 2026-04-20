/**
 * Aujasya — useOcr Hook
 * Manages the full OCR flow: capture → preprocess → recognize → parse.
 * WebWorker cleanup on unmount prevents memory leaks.
 */

'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import type { OcrResult, OcrStatus } from '@/types/ocr.types';
import { preprocessImage } from '@/lib/ocr/image-preprocess';
import { initTesseract, recognizeImage, terminateTesseract } from '@/lib/ocr/tesseract-worker';
import { parsePrescription } from '@/lib/ocr/prescription-parser';

export function useOcr() {
  const [status, setStatus] = useState<OcrStatus>('idle');
  const [result, setResult] = useState<OcrResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const mountedRef = useRef(true);

  // Cleanup Tesseract worker on unmount
  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      terminateTesseract();
    };
  }, []);

  const scanPrescription = useCallback(async (file: File) => {
    try {
      setStatus('preprocessing');
      setError(null);
      setProgress(0);

      // Step 1: Preprocess
      const processed = await preprocessImage(file);

      if (!mountedRef.current) return;
      setStatus('recognizing');

      // Step 2: Initialize Tesseract (cached after first load)
      await initTesseract((p) => {
        if (mountedRef.current) setProgress(p);
      });

      // Step 3: OCR recognition
      const tessResult = await recognizeImage(processed);

      if (!mountedRef.current) return;
      setStatus('parsing');

      // Step 4: Parse entities
      const entities = parsePrescription(tessResult.text);

      const ocrResult: OcrResult = {
        rawText: tessResult.text,
        confidence: tessResult.confidence,
        source: 'tesseract',
        entities,
        ...(tessResult.confidence < 0.65 ? {
          confidenceFlag: 'low' as const,
          userWarning: 'Low confidence — please review all fields carefully',
        } : {}),
      };

      if (mountedRef.current) {
        setResult(ocrResult);
        setStatus('done');
      }
    } catch (err) {
      if (mountedRef.current) {
        setError(err instanceof Error ? err.message : 'OCR failed');
        setStatus('error');
      }
    }
  }, []);

  const reset = useCallback(() => {
    setStatus('idle');
    setResult(null);
    setError(null);
    setProgress(0);
  }, []);

  return { status, result, error, progress, scanPrescription, reset };
}
