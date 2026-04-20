/**
 * Aujasya — Pill Worker Entry Point
 * Actual WebWorker script that runs off main thread.
 * Handles LOAD_MODEL, IDENTIFY, and DISPOSE messages.
 * DISPOSE calls tf.disposeVariables() to prevent WASM memory leaks.
 */

import { loadPillModel, identifyPill, disposePillModel } from './pill-model';

self.onmessage = async (e: MessageEvent) => {
  const msg = e.data;

  switch (msg.type) {
    case 'LOAD_MODEL':
      try {
        await loadPillModel((loaded, total) => {
          self.postMessage({ type: 'MODEL_PROGRESS', loaded, total });
        });
        self.postMessage({ type: 'MODEL_LOADED' });
      } catch (error) {
        self.postMessage({ type: 'ERROR', error: String(error) });
      }
      break;

    case 'IDENTIFY':
      try {
        const candidates = await identifyPill(msg.imageData);
        self.postMessage({ type: 'RESULT', candidates });
      } catch (error) {
        self.postMessage({ type: 'ERROR', error: String(error) });
      }
      break;

    case 'DISPOSE':
      await disposePillModel();
      break;
  }
};
