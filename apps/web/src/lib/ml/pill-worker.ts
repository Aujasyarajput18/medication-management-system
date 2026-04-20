/**
 * Aujasya — Pill Worker Manager
 * Wraps the pill-worker-entry WebWorker with typed message passing.
 * Handles lifecycle: create, inference, dispose, terminate.
 */

import type { PillCandidate } from '@/types/pill-id.types';

export type PillWorkerMessage =
  | { type: 'LOAD_MODEL' }
  | { type: 'IDENTIFY'; imageData: ImageData }
  | { type: 'DISPOSE' };

export type PillWorkerResponse =
  | { type: 'MODEL_LOADED' }
  | { type: 'MODEL_PROGRESS'; loaded: number; total: number }
  | { type: 'RESULT'; candidates: PillCandidate[] }
  | { type: 'ERROR'; error: string };

export class PillWorkerManager {
  private worker: Worker | null = null;
  private pendingResolve: ((value: PillCandidate[]) => void) | null = null;
  private pendingReject: ((reason: Error) => void) | null = null;
  private onProgress?: (loaded: number, total: number) => void;

  constructor(onProgress?: (loaded: number, total: number) => void) {
    this.onProgress = onProgress;
  }

  async init(): Promise<void> {
    this.worker = new Worker(
      new URL('./pill-worker-entry', import.meta.url),
      { type: 'module' }
    );

    this.worker.onmessage = (e: MessageEvent<PillWorkerResponse>) => {
      const msg = e.data;
      switch (msg.type) {
        case 'MODEL_LOADED':
          break;
        case 'MODEL_PROGRESS':
          this.onProgress?.(msg.loaded, msg.total);
          break;
        case 'RESULT':
          this.pendingResolve?.(msg.candidates);
          this.pendingResolve = null;
          this.pendingReject = null;
          break;
        case 'ERROR':
          this.pendingReject?.(new Error(msg.error));
          this.pendingResolve = null;
          this.pendingReject = null;
          break;
      }
    };

    this.worker.postMessage({ type: 'LOAD_MODEL' } as PillWorkerMessage);
  }

  async identify(imageData: ImageData): Promise<PillCandidate[]> {
    if (!this.worker) throw new Error('Worker not initialized');

    return new Promise((resolve, reject) => {
      this.pendingResolve = resolve;
      this.pendingReject = reject;
      this.worker!.postMessage({ type: 'IDENTIFY', imageData } as PillWorkerMessage);
    });
  }

  dispose(): void {
    if (this.worker) {
      this.worker.postMessage({ type: 'DISPOSE' } as PillWorkerMessage);
      this.worker.terminate();
      this.worker = null;
    }
  }
}
