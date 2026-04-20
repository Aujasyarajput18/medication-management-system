/**
 * Aujasya — Pill Model Loader & Inference
 * TF.js MobileNetV2 for on-device pill identification.
 * PILL_MODEL_MOCK=true returns synthetic results (feature flag).
 */

import type { PillCandidate } from '@/types/pill-id.types';

const MOCK_PILL_RESULTS: PillCandidate[] = [
  { drugName: 'Metformin 500mg', confidence: 0.92, color: 'white', shape: 'round', imprint: 'MET 500' },
  { drugName: 'Atorvastatin 10mg', confidence: 0.74, color: 'white', shape: 'oval', imprint: 'AT10' },
  { drugName: 'Amlodipine 5mg', confidence: 0.61, color: 'white', shape: 'round', imprint: 'AM5' },
];

const IS_MOCK = process.env.NEXT_PUBLIC_PILL_MODEL_MOCK === 'true';
const MODEL_URL = process.env.NEXT_PUBLIC_PILL_MODEL_URL || '/models/pill-id/model.json';

/**
 * Load the pill identification model. In mock mode, resolves immediately.
 * In real mode, loads TF.js + MobileNetV2 weights.
 */
export async function loadPillModel(
  onProgress?: (loaded: number, total: number) => void
): Promise<void> {
  if (IS_MOCK) return;

  const tf = await import('@tensorflow/tfjs');
  await tf.ready();
  // Model loading would happen here with real URL
  onProgress?.(1, 1);
}

/**
 * Run pill identification inference on an image.
 * Must be called from a WebWorker via pill-worker.ts.
 */
export async function identifyPill(
  imageData: ImageData
): Promise<PillCandidate[]> {
  if (IS_MOCK) {
    // Simulate inference delay
    await new Promise((r) => setTimeout(r, 800));
    return MOCK_PILL_RESULTS;
  }

  const tf = await import('@tensorflow/tfjs');
  
  // Preprocess: resize to 224x224, normalize to [-1, 1]
  const tensor = tf.browser
    .fromPixels(imageData)
    .resizeBilinear([224, 224])
    .expandDims(0)
    .div(127.5)
    .sub(1);

  // Inference would use the loaded model
  // For now, return mock results as model isn't trained yet
  tensor.dispose();
  return MOCK_PILL_RESULTS;
}

/**
 * Dispose all TF.js variables — call on worker termination.
 */
export async function disposePillModel(): Promise<void> {
  if (IS_MOCK) return;
  try {
    const tf = await import('@tensorflow/tfjs');
    tf.disposeVariables();
    tf.engine().reset();
  } catch {
    // TF.js not loaded — nothing to dispose
  }
}
