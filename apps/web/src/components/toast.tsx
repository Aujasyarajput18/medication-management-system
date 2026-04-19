'use client';

/**
 * Aujasya — Toast / Snackbar Component
 * Used for "Dose marked as taken" confirmations and undo actions.
 */

import { useState, useEffect, useCallback } from 'react';

interface Toast {
  id: string;
  message: string;
  type: 'success' | 'error' | 'info';
  action?: { label: string; onClick: () => void };
  duration?: number;
}

let addToastFn: ((toast: Omit<Toast, 'id'>) => void) | null = null;

export function showToast(toast: Omit<Toast, 'id'>) {
  addToastFn?.(toast);
}

export function ToastContainer() {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const addToast = useCallback((toast: Omit<Toast, 'id'>) => {
    const id = crypto.randomUUID();
    setToasts((prev) => [...prev, { ...toast, id }]);

    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, toast.duration || 3000);
  }, []);

  useEffect(() => {
    addToastFn = addToast;
    return () => { addToastFn = null; };
  }, [addToast]);

  const dismiss = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  if (toasts.length === 0) return null;

  const typeStyles = {
    success: 'bg-green-600',
    error: 'bg-red-600',
    info: 'bg-gray-800',
  };

  return (
    <div className="fixed bottom-20 left-4 right-4 z-50 flex flex-col items-center gap-2">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`w-full max-w-sm rounded-xl px-4 py-3 shadow-lg ${typeStyles[toast.type]} text-white flex items-center justify-between animate-slide-up`}
          role="alert"
        >
          <span className="text-sm font-medium">{toast.message}</span>
          <div className="flex items-center gap-2">
            {toast.action && (
              <button
                onClick={() => {
                  toast.action!.onClick();
                  dismiss(toast.id);
                }}
                className="rounded-lg bg-white/20 px-3 py-1 text-xs font-semibold"
              >
                {toast.action.label}
              </button>
            )}
            <button onClick={() => dismiss(toast.id)} className="text-white/60 hover:text-white ml-1">✕</button>
          </div>
        </div>
      ))}
    </div>
  );
}
