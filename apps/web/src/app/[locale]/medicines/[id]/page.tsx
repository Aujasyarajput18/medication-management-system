'use client';

/**
 * Aujasya — Medicine Detail Page
 * Shows full medicine info with schedules, edit, and deactivate.
 */

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useMedicineStore } from '@/stores/medicine-store';
import { useMealAnchorTime } from '@/hooks/use-meal-anchor-time';
import { BottomNav } from '@/components/bottom-nav';

export default function MedicineDetailPage() {
  const t = useTranslations('medicines');
  const tCommon = useTranslations('common');
  const { locale, id } = useParams<{ locale: string; id: string }>();
  const router = useRouter();
  const { medicines, fetchMedicines, deactivateMedicine } = useMedicineStore();
  const { getDisplayName, getTimeForAnchor, formatTime12h } = useMealAnchorTime();
  const [showDeactivate, setShowDeactivate] = useState(false);

  useEffect(() => {
    if (medicines.length === 0) fetchMedicines();
  }, [medicines.length, fetchMedicines]);

  const medicine = medicines.find((m) => m.id === id);

  if (!medicine) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  const handleDeactivate = async () => {
    await deactivateMedicine(medicine.id);
    router.push(`/${locale}/medicines`);
  };

  const dayLabels = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

  return (
    <div className="min-h-screen bg-background pb-24">
      <header className="border-b border-border bg-card px-4 pb-4 pt-safe">
        <div className="flex items-center justify-between pt-4">
          <div className="flex items-center gap-3">
            <button onClick={() => router.back()} className="text-xl">←</button>
            <h1 className="text-xl font-bold">{medicine.brandName}</h1>
          </div>
          <button
            onClick={() => router.push(`/${locale}/medicines/${id}/edit`)}
            className="rounded-lg bg-muted px-3 py-1.5 text-sm font-medium"
          >
            {tCommon('edit')}
          </button>
        </div>
      </header>

      <div className="px-4 pt-4 space-y-4">
        {/* Details card */}
        <div className="rounded-xl border border-border bg-card p-4 space-y-3">
          {medicine.genericName && (
            <div>
              <p className="text-xs text-muted-foreground">{t('genericName')}</p>
              <p className="font-medium">{medicine.genericName}</p>
            </div>
          )}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <p className="text-xs text-muted-foreground">{t('dosage')}</p>
              <p className="font-medium">{medicine.dosageValue} {medicine.dosageUnit}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">{t('form')}</p>
              <p className="font-medium capitalize">{medicine.form}</p>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <p className="text-xs text-muted-foreground">{t('startDate')}</p>
              <p className="font-medium">{medicine.startDate}</p>
            </div>
            {medicine.endDate && (
              <div>
                <p className="text-xs text-muted-foreground">{t('endDate')}</p>
                <p className="font-medium">{medicine.endDate}</p>
              </div>
            )}
          </div>
          {medicine.prescribedBy && (
            <div>
              <p className="text-xs text-muted-foreground">{t('prescribedBy')}</p>
              <p className="font-medium">{medicine.prescribedBy}</p>
            </div>
          )}
          {medicine.instructions && (
            <div>
              <p className="text-xs text-muted-foreground">{t('instructions')}</p>
              <p className="text-sm">{medicine.instructions}</p>
            </div>
          )}
        </div>

        {/* Quantity progress */}
        {medicine.totalQuantity != null && medicine.remainingQuantity != null && (
          <div className="rounded-xl border border-border bg-card p-4">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">{t('remaining')}</span>
              <span className="font-medium">{medicine.remainingQuantity} / {medicine.totalQuantity}</span>
            </div>
            <div className="mt-2 h-2 rounded-full bg-muted">
              <div className="h-full rounded-full bg-primary transition-all"
                style={{ width: `${(medicine.remainingQuantity / medicine.totalQuantity) * 100}%` }} />
            </div>
          </div>
        )}

        {/* Schedules */}
        <div className="rounded-xl border border-border bg-card p-4">
          <h3 className="font-semibold mb-3">{t('schedule')}</h3>
          <div className="space-y-3">
            {medicine.schedules.map((schedule) => {
              const time = getTimeForAnchor(schedule.mealAnchor);
              return (
                <div key={schedule.id} className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-sm">{getDisplayName(schedule.mealAnchor, locale)}</p>
                    {time && <p className="text-xs text-muted-foreground">{formatTime12h(time)}</p>}
                    <p className="text-xs text-muted-foreground">
                      {schedule.daysOfWeek.length === 7
                        ? 'Daily'
                        : schedule.daysOfWeek.map((d) => dayLabels[d]).join(', ')}
                    </p>
                  </div>
                  <span className="text-sm text-muted-foreground">× {schedule.doseQuantity}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Deactivate */}
        <button
          onClick={() => setShowDeactivate(true)}
          className="w-full rounded-xl border border-destructive/30 py-3 text-sm font-medium text-destructive"
        >
          Deactivate Medicine
        </button>
      </div>

      {/* Deactivate confirmation modal */}
      {showDeactivate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 px-6">
          <div className="w-full max-w-sm rounded-2xl bg-card p-6 shadow-xl">
            <h3 className="text-lg font-semibold">Deactivate {medicine.brandName}?</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              This will stop all reminders and future dose generation for this medicine.
            </p>
            <div className="mt-4 flex gap-3">
              <button onClick={() => setShowDeactivate(false)}
                className="flex-1 rounded-xl border border-border py-3 text-sm font-medium">{tCommon('cancel')}</button>
              <button onClick={handleDeactivate}
                className="flex-1 rounded-xl bg-destructive py-3 text-sm font-medium text-white">{tCommon('confirm')}</button>
            </div>
          </div>
        </div>
      )}

      <BottomNav locale={locale} />
    </div>
  );
}
