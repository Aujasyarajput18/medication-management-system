'use client';

/**
 * Aujasya — 5-Step Onboarding Page
 * Steps: Name → DOB → Language → Meal Times → Complete
 *
 * [Issue #10] Partial completion state is persisted to the backend via
 * PATCH /api/bff/auth/me on each step completion (not localStorage — DPDPA).
 * If the user closes mid-onboarding and returns later:
 *   1. initializeAuth() restores their session
 *   2. Settings page shows "Complete Setup" if profile is incomplete
 *   3. User can navigate here from Settings to resume from the last incomplete step
 *
 * Completion detection: a profile is "complete" when full_name, date_of_birth,
 * and preferred_language are all non-null.
 */

import { useState, useMemo } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useAuthStore } from '@/stores/auth-store';
import api from '@/lib/api-client';

const DEFAULT_MEAL_TIMES = {
  breakfast: '08:00',
  lunch: '13:00',
  dinner: '20:00',
  bedtime: '22:00',
  waking: '06:00',
};

export default function OnboardingPage() {
  const t = useTranslations('onboarding');
  const tCommon = useTranslations('common');
  const { locale } = useParams<{ locale: string }>();
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const updateProfile = useAuthStore((s) => s.updateProfile);

  // [Issue #10] Determine starting step from existing profile data
  const initialStep = useMemo(() => {
    if (!user) return 0;
    if (!user.fullName) return 0;
    if (!user.dateOfBirth) return 1;
    if (!user.preferredLanguage || user.preferredLanguage === 'hi') return 2;
    return 3; // Meal times
  }, [user]);

  const [step, setStep] = useState(initialStep);
  const [fullName, setFullName] = useState(user?.fullName || '');
  const [dob, setDob] = useState(user?.dateOfBirth || '');
  const [language, setLanguage] = useState(user?.preferredLanguage || locale || 'hi');
  const [mealTimes, setMealTimes] = useState(DEFAULT_MEAL_TIMES);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState('');

  const totalSteps = 5;

  // [Issue #10] Save progress to backend on each step completion
  const saveStepProgress = async (data: Record<string, any>) => {
    setIsSaving(true);
    setError('');
    try {
      await updateProfile(data);
      return true;
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save');
      return false;
    } finally {
      setIsSaving(false);
    }
  };

  const handleNext = async () => {
    let success = true;

    switch (step) {
      case 0: // Name
        if (fullName.trim().length < 2) {
          setError('Name must be at least 2 characters');
          return;
        }
        success = await saveStepProgress({ fullName: fullName.trim() });
        break;

      case 1: // DOB
        if (!dob) {
          setError('Please select your date of birth');
          return;
        }
        success = await saveStepProgress({ dateOfBirth: dob });
        break;

      case 2: // Language
        success = await saveStepProgress({ preferredLanguage: language });
        break;

      case 3: // Meal times
        try {
          await api.post('/settings/meal-times', { meal_times: mealTimes });
          success = true;
        } catch {
          success = true; // Non-critical — use defaults
        }
        break;

      case 4: // Complete
        router.push(`/${language}/today`);
        return;
    }

    if (success) {
      setStep((s) => Math.min(s + 1, totalSteps - 1));
      setError('');
    }
  };

  const handleBack = () => {
    setStep((s) => Math.max(s - 1, 0));
    setError('');
  };

  const handleSkip = () => {
    setStep((s) => Math.min(s + 1, totalSteps - 1));
    setError('');
  };

  const languages = [
    { code: 'hi', name: 'हिंदी' },
    { code: 'en', name: 'English' },
    { code: 'ta', name: 'தமிழ்' },
    { code: 'te', name: 'తెలుగు' },
    { code: 'bn', name: 'বাংলা' },
    { code: 'mr', name: 'मराठी' },
  ];

  return (
    <div className="flex min-h-screen flex-col bg-background px-6 pt-safe">
      {/* Progress bar */}
      <div className="pt-6 pb-4">
        <div className="flex gap-1.5">
          {Array.from({ length: totalSteps }).map((_, i) => (
            <div
              key={i}
              className={`h-1.5 flex-1 rounded-full transition-colors ${
                i <= step ? 'bg-primary' : 'bg-muted'
              }`}
            />
          ))}
        </div>
        <p className="mt-2 text-xs text-muted-foreground text-right">
          {step + 1}/{totalSteps}
        </p>
      </div>

      <div className="flex-1 flex flex-col justify-center max-w-sm mx-auto w-full">
        {/* Step 0: Name */}
        {step === 0 && (
          <div className="space-y-4">
            <h1 className="text-2xl font-bold">{t('nameLabel')}</h1>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder={t('namePlaceholder')}
              className="w-full rounded-xl border border-input bg-background px-4 py-3.5 text-lg focus:border-primary focus:outline-none focus:ring-2 focus:ring-ring"
              autoFocus
            />
          </div>
        )}

        {/* Step 1: Date of Birth */}
        {step === 1 && (
          <div className="space-y-4">
            <h1 className="text-2xl font-bold">{t('dobLabel')}</h1>
            <input
              type="date"
              value={dob}
              onChange={(e) => setDob(e.target.value)}
              max={new Date().toISOString().split('T')[0]}
              className="w-full rounded-xl border border-input bg-background px-4 py-3.5 text-lg focus:border-primary focus:outline-none focus:ring-2 focus:ring-ring"
            />
          </div>
        )}

        {/* Step 2: Language */}
        {step === 2 && (
          <div className="space-y-4">
            <h1 className="text-2xl font-bold">{t('languageLabel')}</h1>
            <div className="grid grid-cols-2 gap-3">
              {languages.map((lang) => (
                <button
                  key={lang.code}
                  onClick={() => setLanguage(lang.code)}
                  className={`rounded-xl border-2 p-4 text-left transition-all ${
                    language === lang.code
                      ? 'border-primary bg-primary/5 ring-2 ring-primary/20'
                      : 'border-border hover:border-primary/50'
                  }`}
                >
                  <span className="text-lg font-medium">{lang.name}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Step 3: Meal Times */}
        {step === 3 && (
          <div className="space-y-4">
            <h1 className="text-2xl font-bold">{t('mealTimesTitle')}</h1>
            <p className="text-sm text-muted-foreground">{t('mealTimesSubtitle')}</p>
            <div className="space-y-3">
              {(Object.entries(mealTimes) as [keyof typeof DEFAULT_MEAL_TIMES, string][]).map(
                ([meal, time]) => (
                  <div key={meal} className="flex items-center justify-between rounded-xl border border-border p-3">
                    <span className="font-medium">{t(meal)}</span>
                    <input
                      type="time"
                      value={time}
                      onChange={(e) =>
                        setMealTimes((prev) => ({ ...prev, [meal]: e.target.value }))
                      }
                      className="rounded-lg border border-input bg-background px-3 py-1.5 text-sm"
                    />
                  </div>
                )
              )}
            </div>
          </div>
        )}

        {/* Step 4: Complete */}
        {step === 4 && (
          <div className="text-center space-y-4">
            <span className="text-7xl">🎉</span>
            <h1 className="text-2xl font-bold">{t('complete')}</h1>
            <p className="text-muted-foreground">
              {tCommon('appName')} is ready for you!
            </p>
          </div>
        )}

        {error && (
          <p className="mt-3 text-sm text-destructive">{error}</p>
        )}
      </div>

      {/* Navigation buttons */}
      <div className="pb-8 pt-4 flex gap-3 max-w-sm mx-auto w-full">
        {step > 0 && step < 4 && (
          <button
            onClick={handleBack}
            className="flex-1 rounded-xl border border-border py-3.5 text-sm font-medium"
          >
            {tCommon('back')}
          </button>
        )}
        {/* Skip button for optional steps (DOB, meal times) */}
        {(step === 1 || step === 3) && (
          <button
            onClick={handleSkip}
            className="rounded-xl px-4 py-3.5 text-sm text-muted-foreground hover:text-foreground"
          >
            Skip
          </button>
        )}
        <button
          onClick={handleNext}
          disabled={isSaving}
          className="flex-1 rounded-xl bg-primary py-3.5 text-sm font-semibold text-primary-foreground shadow-md disabled:opacity-50"
        >
          {isSaving ? (
            <span className="flex items-center justify-center gap-2">
              <span className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
            </span>
          ) : step === 4 ? (
            t('complete')
          ) : (
            tCommon('next')
          )}
        </button>
      </div>
    </div>
  );
}
