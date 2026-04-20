/**
 * Aujasya — Tesseract WebWorker Manager
 * Manages Tesseract.js worker lifecycle for client-side OCR.
 * Runs entirely off main thread. Supports Hindi + English.
 */

import { createWorker, type Worker } from 'tesseract.js';

export interface TesseractResult {
  text: string;
  confidence: number;
  words: Array<{ text: string; confidence: number }>;
}

let workerInstance: Worker | null = null;
let isInitializing = false;

/**
 * Initialize Tesseract worker with Hindi + English language packs.
 * Cached after first load (~2-3MB download).
 */
export async function initTesseract(
  onProgress?: (progress: number) => void
): Promise<void> {
  if (workerInstance || isInitializing) return;
  isInitializing = true;

  try {
    workerInstance = await createWorker('eng+hin', undefined, {
      logger: (m) => {
        if (m.status === 'recognizing text' && onProgress) {
          onProgress(m.progress);
        }
      },
    });
    isInitializing = false;
  } catch (error) {
    isInitializing = false;
    throw error;
  }
}

/**
 * Run OCR on a preprocessed image blob.
 * Returns text, confidence, and per-word breakdowns.
 */
export async function recognizeImage(
  imageBlob: Blob
): Promise<TesseractResult> {
  if (!workerInstance) {
    await initTesseract();
  }

  const { data } = await workerInstance!.recognize(imageBlob);
  const words = (
    data as unknown as { words?: Array<{ text: string; confidence: number }> }
  ).words ?? [];

  return {
    text: data.text.trim(),
    confidence: data.confidence / 100, // Normalize to 0-1
    words: words.map((w) => ({
      text: w.text,
      confidence: w.confidence / 100,
    })),
  };
}

/**
 * Terminate the Tesseract worker — MUST be called on page unmount.
 */
export async function terminateTesseract(): Promise<void> {
  if (workerInstance) {
    await workerInstance.terminate();
    workerInstance = null;
  }
}
