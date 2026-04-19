'use client';

/**
 * Aujasya — Login Page
 * Phone number input with E.164 validation for Indian numbers.
 */

import { useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useAuthStore } from '@/stores/auth-store';

export default function LoginPage() {
  const t = useTranslations('auth');
  const { locale } = useParams<{ locale: string }>();
  const router = useRouter();
  const sendOtp = useAuthStore((s) => s.sendOtp);

  const [phone, setPhone] = useState('+91');
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isValidPhone = /^\+91[6-9]\d{9}$/.test(phone);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isValidPhone) {
      setError(t('invalidPhone'));
      return;
    }

    setIsSubmitting(true);
    setError('');

    try {
      const { sessionId } = await sendOtp(phone);
      router.push(`/${locale}/verify?session=${sessionId}&phone=${encodeURIComponent(phone)}`);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || t('error'));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-b from-primary/5 via-background to-background px-6">
      {/* Logo */}
      <div className="mb-8 flex flex-col items-center">
        <div className="flex h-20 w-20 items-center justify-center rounded-2xl bg-primary shadow-lg">
          <span className="text-4xl">💊</span>
        </div>
        <h1 className="mt-4 text-3xl font-bold text-foreground">{t('title')}</h1>
        <p className="mt-2 text-muted-foreground">{t('subtitle')}</p>
      </div>

      {/* Phone Form */}
      <form onSubmit={handleSubmit} className="w-full max-w-sm space-y-4">
        <div>
          <label
            htmlFor="phone"
            className="mb-1.5 block text-sm font-medium text-foreground"
          >
            {t('phoneLabel')}
          </label>
          <input
            id="phone"
            type="tel"
            inputMode="tel"
            autoComplete="tel"
            value={phone}
            onChange={(e) => {
              setPhone(e.target.value);
              setError('');
            }}
            placeholder={t('phonePlaceholder')}
            className="w-full rounded-xl border border-input bg-background px-4 py-3.5 text-lg font-medium tracking-wider shadow-sm transition-colors focus:border-primary focus:outline-none focus:ring-2 focus:ring-ring"
            maxLength={13}
            aria-describedby={error ? 'phone-error' : undefined}
            aria-invalid={!!error}
          />
          {error && (
            <p id="phone-error" className="mt-1.5 text-sm text-destructive" role="alert">
              {error}
            </p>
          )}
        </div>

        <button
          type="submit"
          disabled={!isValidPhone || isSubmitting}
          className="w-full rounded-xl bg-primary py-4 text-lg font-semibold text-primary-foreground shadow-md transition-all hover:bg-primary/90 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isSubmitting ? (
            <span className="flex items-center justify-center gap-2">
              <span className="h-5 w-5 animate-spin rounded-full border-2 border-white border-t-transparent" />
              {t('sendOtp')}...
            </span>
          ) : (
            t('sendOtp')
          )}
        </button>
      </form>

      {/* Language hint */}
      <p className="mt-8 text-xs text-muted-foreground">
        🇮🇳 हिंदी · English · தமிழ் · తెలుగు · বাংলা · मराठी
      </p>
    </div>
  );
}
