'use client';

/**
 * Aujasya — OTP Verification Page
 * 6-digit OTP input with auto-submit, countdown timer, and resend.
 */

import { useState, useRef, useEffect } from 'react';
import { useRouter, useSearchParams, useParams } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useAuthStore } from '@/stores/auth-store';
import { useCountdown } from '@/hooks/use-countdown';

export default function VerifyPage() {
  const t = useTranslations('auth');
  const { locale } = useParams<{ locale: string }>();
  const router = useRouter();
  const searchParams = useSearchParams();
  const sessionId = searchParams.get('session') || '';
  const phone = searchParams.get('phone') || '';

  const verifyOtp = useAuthStore((s) => s.verifyOtp);
  const sendOtp = useAuthStore((s) => s.sendOtp);
  const isNewUser = useAuthStore((s) => s.isNewUser);

  const [otp, setOtp] = useState(['', '', '', '', '', '']);
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [currentSession, setCurrentSession] = useState(sessionId);
  const inputRefs = useRef<(HTMLInputElement | null)[]>([]);
  const { seconds, isActive, start } = useCountdown(60);

  // Start countdown on mount
  useEffect(() => {
    start();
  }, [start]);

  const handleChange = (index: number, value: string) => {
    if (value.length > 1) {
      // Handle paste
      const digits = value.replace(/\D/g, '').slice(0, 6).split('');
      const newOtp = [...otp];
      digits.forEach((d, i) => {
        if (index + i < 6) newOtp[index + i] = d;
      });
      setOtp(newOtp);
      const nextIndex = Math.min(index + digits.length, 5);
      inputRefs.current[nextIndex]?.focus();

      // Auto-submit if all 6 digits filled
      if (newOtp.every((d) => d !== '')) {
        handleSubmit(newOtp.join(''));
      }
      return;
    }

    if (!/^\d?$/.test(value)) return;
    const newOtp = [...otp];
    newOtp[index] = value;
    setOtp(newOtp);

    if (value && index < 5) {
      inputRefs.current[index + 1]?.focus();
    }

    // Auto-submit
    if (value && newOtp.every((d) => d !== '')) {
      handleSubmit(newOtp.join(''));
    }
  };

  const handleKeyDown = (index: number, e: React.KeyboardEvent) => {
    if (e.key === 'Backspace' && !otp[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  };

  const handleSubmit = async (otpString?: string) => {
    const code = otpString || otp.join('');
    if (code.length !== 6) {
      setError(t('invalidOtp'));
      return;
    }

    setIsSubmitting(true);
    setError('');

    try {
      await verifyOtp(currentSession, code);
      if (isNewUser) {
        router.push(`/${locale}/onboarding`);
      } else {
        router.push(`/${locale}/today`);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || t('invalidOtp'));
      setOtp(['', '', '', '', '', '']);
      inputRefs.current[0]?.focus();
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleResend = async () => {
    try {
      const { sessionId: newSession } = await sendOtp(phone);
      setCurrentSession(newSession);
      setOtp(['', '', '', '', '', '']);
      setError('');
      start();
      inputRefs.current[0]?.focus();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to resend OTP');
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-6">
      <div className="w-full max-w-sm">
        {/* Header */}
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10">
            <span className="text-3xl">🔐</span>
          </div>
          <h1 className="text-2xl font-bold">{t('otpTitle')}</h1>
          <p className="mt-2 text-sm text-muted-foreground">
            {t('otpSubtitle')} <br />
            <span className="font-medium text-foreground">{phone}</span>
          </p>
        </div>

        {/* OTP Input */}
        <div className="flex justify-center gap-3">
          {otp.map((digit, i) => (
            <input
              key={i}
              ref={(el) => { inputRefs.current[i] = el; }}
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              maxLength={6}
              value={digit}
              onChange={(e) => handleChange(i, e.target.value)}
              onKeyDown={(e) => handleKeyDown(i, e)}
              className="h-14 w-12 rounded-xl border-2 border-input bg-background text-center text-2xl font-bold transition-all focus:border-primary focus:outline-none focus:ring-2 focus:ring-ring"
              aria-label={`Digit ${i + 1}`}
              autoFocus={i === 0}
            />
          ))}
        </div>

        {error && (
          <p className="mt-3 text-center text-sm text-destructive" role="alert">
            {error}
          </p>
        )}

        {/* Verify button */}
        <button
          onClick={() => handleSubmit()}
          disabled={otp.some((d) => !d) || isSubmitting}
          className="mt-6 w-full rounded-xl bg-primary py-4 text-lg font-semibold text-primary-foreground shadow-md transition-all disabled:opacity-50"
        >
          {isSubmitting ? (
            <span className="flex items-center justify-center gap-2">
              <span className="h-5 w-5 animate-spin rounded-full border-2 border-white border-t-transparent" />
              {t('verifyOtp')}...
            </span>
          ) : (
            t('verifyOtp')
          )}
        </button>

        {/* Resend */}
        <div className="mt-6 text-center">
          {isActive ? (
            <p className="text-sm text-muted-foreground">
              {t('resendIn', { seconds })}
            </p>
          ) : (
            <button
              onClick={handleResend}
              className="text-sm font-medium text-primary hover:underline"
            >
              {t('resendOtp')}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
