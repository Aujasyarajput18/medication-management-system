'use client';

/**
 * Aujasya — Medicines Page
 * List all medicines with add button.
 */

import { useEffect } from 'react';
import { useTranslations } from 'next-intl';
import { useParams } from 'next/navigation';
import { useMedicineStore } from '@/stores/medicine-store';
import { BottomNav } from '@/components/bottom-nav';

export default function MedicinesPage() {
  const t = useTranslations('medicines');
  const { locale } = useParams<{ locale: string }>();
  const { medicines, isLoading, fetchMedicines } = useMedicineStore();

  useEffect(() => {
    fetchMedicines();
  }, [fetchMedicines]);

  return (
    <div className="min-h-screen bg-background pb-24">
      {/* Header */}
      <header className="border-b border-border bg-card px-4 pb-4 pt-safe">
        <div className="flex items-center justify-between pt-4">
          <h1 className="text-2xl font-bold">{t('title')}</h1>
          <button className="rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground shadow-sm transition-all active:scale-95">
            + {t('addNew')}
          </button>
        </div>
      </header>

      <div className="px-4 pt-4">
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          </div>
        ) : medicines.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <span className="text-6xl mb-4">💊</span>
            <p className="text-lg font-medium text-muted-foreground">{t('noMedicines')}</p>
            <p className="mt-1 text-sm text-muted-foreground">{t('addFirst')}</p>
          </div>
        ) : (
          <div className="space-y-3">
            {medicines.map((med) => (
              <div
                key={med.id}
                className="rounded-xl border border-border bg-card p-4 shadow-sm"
              >
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-semibold text-foreground">{med.brandName}</h3>
                    {med.genericName && (
                      <p className="text-sm text-muted-foreground">{med.genericName}</p>
                    )}
                    <p className="mt-1 text-sm text-muted-foreground">
                      {med.dosageValue} {med.dosageUnit} · {med.form}
                    </p>
                  </div>
                  <span
                    className={`rounded-full px-2.5 py-1 text-xs font-medium ${
                      med.isActive
                        ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                        : 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'
                    }`}
                  >
                    {med.isActive ? t('active') : t('inactive')}
                  </span>
                </div>

                {med.schedules.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-2">
                    {med.schedules.map((s) => (
                      <span
                        key={s.id}
                        className="rounded-lg bg-primary/10 px-2.5 py-1 text-xs font-medium text-primary"
                      >
                        {s.mealAnchor.replace(/_/g, ' ')}
                      </span>
                    ))}
                  </div>
                )}

                {med.remainingQuantity != null && med.totalQuantity != null && (
                  <div className="mt-3">
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <span>{t('remaining')}: {med.remainingQuantity}</span>
                      <span>{Math.round((med.remainingQuantity / med.totalQuantity) * 100)}%</span>
                    </div>
                    <div className="mt-1 h-1.5 rounded-full bg-muted">
                      <div
                        className="h-full rounded-full bg-primary transition-all"
                        style={{ width: `${(med.remainingQuantity / med.totalQuantity) * 100}%` }}
                      />
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      <BottomNav locale={locale} />
    </div>
  );
}
