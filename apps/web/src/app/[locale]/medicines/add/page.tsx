'use client';

/**
 * Aujasya — Add Medicine Page
 * Multi-step form: medicine details → schedule(s) → confirmation.
 */

import { useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useMedicineStore } from '@/stores/medicine-store';
import { BottomNav } from '@/components/bottom-nav';

const FORMS = ['tablet', 'capsule', 'syrup', 'injection', 'drops', 'cream', 'inhaler', 'other'];
const MEAL_ANCHORS = [
  'on_waking', 'before_breakfast', 'with_breakfast', 'after_breakfast',
  'before_lunch', 'with_lunch', 'after_lunch',
  'before_dinner', 'with_dinner', 'after_dinner', 'at_bedtime', 'any_time',
];

interface ScheduleInput {
  mealAnchor: string;
  doseQuantity: number;
  daysOfWeek: number[];
}

export default function AddMedicinePage() {
  const t = useTranslations('medicines');
  const tCommon = useTranslations('common');
  const { locale } = useParams<{ locale: string }>();
  const router = useRouter();
  const addMedicine = useMedicineStore((s) => s.addMedicine);

  const [step, setStep] = useState(0); // 0: details, 1: schedule, 2: confirm
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  // Medicine fields
  const [brandName, setBrandName] = useState('');
  const [genericName, setGenericName] = useState('');
  const [dosageValue, setDosageValue] = useState('');
  const [dosageUnit, setDosageUnit] = useState('mg');
  const [form, setForm] = useState('tablet');
  const [startDate, setStartDate] = useState(new Date().toISOString().split('T')[0]);
  const [endDate, setEndDate] = useState('');
  const [prescribedBy, setPrescribedBy] = useState('');
  const [instructions, setInstructions] = useState('');
  const [totalQuantity, setTotalQuantity] = useState('');

  // Schedules
  const [schedules, setSchedules] = useState<ScheduleInput[]>([
    { mealAnchor: 'after_breakfast', doseQuantity: 1, daysOfWeek: [0, 1, 2, 3, 4, 5, 6] },
  ]);

  const addSchedule = () => {
    setSchedules([
      ...schedules,
      { mealAnchor: 'after_dinner', doseQuantity: 1, daysOfWeek: [0, 1, 2, 3, 4, 5, 6] },
    ]);
  };

  const removeSchedule = (index: number) => {
    if (schedules.length > 1) {
      setSchedules(schedules.filter((_, i) => i !== index));
    }
  };

  const updateSchedule = (index: number, field: keyof ScheduleInput, value: any) => {
    setSchedules(schedules.map((s, i) => (i === index ? { ...s, [field]: value } : s)));
  };

  const toggleDay = (scheduleIndex: number, day: number) => {
    const schedule = schedules[scheduleIndex];
    const newDays = schedule.daysOfWeek.includes(day)
      ? schedule.daysOfWeek.filter((d) => d !== day)
      : [...schedule.daysOfWeek, day].sort();
    updateSchedule(scheduleIndex, 'daysOfWeek', newDays);
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    setError('');
    try {
      await addMedicine({
        brand_name: brandName,
        generic_name: genericName || null,
        dosage_value: parseFloat(dosageValue),
        dosage_unit: dosageUnit,
        form,
        start_date: startDate,
        end_date: endDate || null,
        prescribed_by: prescribedBy || null,
        instructions: instructions || null,
        total_quantity: totalQuantity ? parseInt(totalQuantity) : null,
        schedules: schedules.map((s) => ({
          meal_anchor: s.mealAnchor,
          dose_quantity: s.doseQuantity,
          days_of_week: s.daysOfWeek,
        })),
      });
      router.push(`/${locale}/medicines`);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to add medicine');
    } finally {
      setIsSubmitting(false);
    }
  };

  const dayLabels = ['S', 'M', 'T', 'W', 'T', 'F', 'S'];

  return (
    <div className="min-h-screen bg-background pb-24">
      <header className="border-b border-border bg-card px-4 pb-4 pt-safe">
        <div className="flex items-center gap-3 pt-4">
          <button onClick={() => router.back()} className="text-xl">←</button>
          <h1 className="text-xl font-bold">{t('addNew')}</h1>
        </div>
        {/* Step indicator */}
        <div className="mt-3 flex gap-1.5">
          {[0, 1, 2].map((i) => (
            <div key={i} className={`h-1 flex-1 rounded-full ${i <= step ? 'bg-primary' : 'bg-muted'}`} />
          ))}
        </div>
      </header>

      <div className="px-4 pt-4 max-w-lg mx-auto">
        {/* Step 0: Medicine Details */}
        {step === 0 && (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1.5">{t('brandName')} *</label>
              <input type="text" value={brandName} onChange={(e) => setBrandName(e.target.value)}
                className="w-full rounded-xl border border-input bg-background px-4 py-3 focus:border-primary focus:outline-none focus:ring-2 focus:ring-ring" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1.5">{t('genericName')}</label>
              <input type="text" value={genericName} onChange={(e) => setGenericName(e.target.value)}
                className="w-full rounded-xl border border-input bg-background px-4 py-3 focus:border-primary focus:outline-none focus:ring-2 focus:ring-ring" />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium mb-1.5">{t('dosage')} *</label>
                <input type="number" value={dosageValue} onChange={(e) => setDosageValue(e.target.value)}
                  step="0.5" min="0" className="w-full rounded-xl border border-input bg-background px-4 py-3 focus:border-primary focus:outline-none focus:ring-2 focus:ring-ring" />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1.5">Unit *</label>
                <select value={dosageUnit} onChange={(e) => setDosageUnit(e.target.value)}
                  className="w-full rounded-xl border border-input bg-background px-4 py-3 focus:outline-none">
                  {['mg', 'g', 'ml', 'drops', 'units', 'puffs'].map((u) => <option key={u} value={u}>{u}</option>)}
                </select>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1.5">{t('form')} *</label>
              <div className="flex flex-wrap gap-2">
                {FORMS.map((f) => (
                  <button key={f} onClick={() => setForm(f)}
                    className={`rounded-lg px-3 py-1.5 text-sm font-medium capitalize transition-colors ${
                      form === f ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'}`}>
                    {f}
                  </button>
                ))}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium mb-1.5">{t('startDate')} *</label>
                <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)}
                  className="w-full rounded-xl border border-input bg-background px-4 py-3 focus:outline-none" />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1.5">{t('endDate')}</label>
                <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)}
                  className="w-full rounded-xl border border-input bg-background px-4 py-3 focus:outline-none" />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1.5">{t('prescribedBy')}</label>
              <input type="text" value={prescribedBy} onChange={(e) => setPrescribedBy(e.target.value)}
                className="w-full rounded-xl border border-input bg-background px-4 py-3 focus:outline-none" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1.5">{t('instructions')}</label>
              <textarea value={instructions} onChange={(e) => setInstructions(e.target.value)} rows={2}
                className="w-full rounded-xl border border-input bg-background px-4 py-3 focus:outline-none" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1.5">{t('quantity')}</label>
              <input type="number" value={totalQuantity} onChange={(e) => setTotalQuantity(e.target.value)}
                min="0" className="w-full rounded-xl border border-input bg-background px-4 py-3 focus:outline-none" />
            </div>
          </div>
        )}

        {/* Step 1: Schedules */}
        {step === 1 && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold">{t('schedule')}</h2>
            {schedules.map((schedule, i) => (
              <div key={i} className="rounded-xl border border-border p-4 space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">Schedule {i + 1}</span>
                  {schedules.length > 1 && (
                    <button onClick={() => removeSchedule(i)} className="text-xs text-destructive">Remove</button>
                  )}
                </div>
                <select value={schedule.mealAnchor} onChange={(e) => updateSchedule(i, 'mealAnchor', e.target.value)}
                  className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm">
                  {MEAL_ANCHORS.map((a) => <option key={a} value={a}>{a.replace(/_/g, ' ')}</option>)}
                </select>
                <div>
                  <label className="text-xs text-muted-foreground">Quantity per dose</label>
                  <input type="number" value={schedule.doseQuantity} min="0.5" step="0.5"
                    onChange={(e) => updateSchedule(i, 'doseQuantity', parseFloat(e.target.value) || 1)}
                    className="w-full rounded-lg border border-input bg-background px-3 py-2 text-sm mt-1" />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground mb-1 block">Days (0=Sun)</label>
                  <div className="flex gap-1.5">
                    {dayLabels.map((label, day) => (
                      <button key={day} onClick={() => toggleDay(i, day)}
                        className={`h-9 w-9 rounded-lg text-xs font-medium transition-colors ${
                          schedule.daysOfWeek.includes(day) ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'}`}>
                        {label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            ))}
            <button onClick={addSchedule}
              className="w-full rounded-xl border-2 border-dashed border-border py-3 text-sm text-muted-foreground hover:border-primary hover:text-primary">
              + Add another schedule
            </button>
          </div>
        )}

        {/* Step 2: Confirmation */}
        {step === 2 && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold">Confirm</h2>
            <div className="rounded-xl border border-border bg-card p-4 space-y-2">
              <p><span className="text-muted-foreground text-sm">{t('brandName')}:</span> <strong>{brandName}</strong></p>
              {genericName && <p><span className="text-muted-foreground text-sm">{t('genericName')}:</span> {genericName}</p>}
              <p><span className="text-muted-foreground text-sm">{t('dosage')}:</span> {dosageValue} {dosageUnit}</p>
              <p><span className="text-muted-foreground text-sm">{t('form')}:</span> {form}</p>
              <p><span className="text-muted-foreground text-sm">{t('startDate')}:</span> {startDate}</p>
              {endDate && <p><span className="text-muted-foreground text-sm">{t('endDate')}:</span> {endDate}</p>}
              <div className="pt-2 border-t border-border mt-2">
                <p className="text-sm font-medium mb-1">{t('schedule')}:</p>
                {schedules.map((s, i) => (
                  <p key={i} className="text-sm text-muted-foreground">
                    {s.mealAnchor.replace(/_/g, ' ')} × {s.doseQuantity} · {s.daysOfWeek.length === 7 ? 'Daily' : `${s.daysOfWeek.length} days/week`}
                  </p>
                ))}
              </div>
            </div>
          </div>
        )}

        {error && <p className="mt-3 text-sm text-destructive">{error}</p>}
      </div>

      {/* Navigation */}
      <div className="fixed bottom-16 left-0 right-0 border-t border-border bg-card px-4 py-3">
        <div className="max-w-lg mx-auto flex gap-3">
          {step > 0 && (
            <button onClick={() => setStep(step - 1)}
              className="flex-1 rounded-xl border border-border py-3 text-sm font-medium">
              {tCommon('back')}
            </button>
          )}
          {step < 2 ? (
            <button onClick={() => setStep(step + 1)}
              disabled={step === 0 && (!brandName || !dosageValue)}
              className="flex-1 rounded-xl bg-primary py-3 text-sm font-semibold text-primary-foreground disabled:opacity-50">
              {tCommon('next')}
            </button>
          ) : (
            <button onClick={handleSubmit} disabled={isSubmitting}
              className="flex-1 rounded-xl bg-primary py-3 text-sm font-semibold text-primary-foreground disabled:opacity-50">
              {isSubmitting ? '...' : tCommon('save')}
            </button>
          )}
        </div>
      </div>

      <BottomNav locale={locale} />
    </div>
  );
}
