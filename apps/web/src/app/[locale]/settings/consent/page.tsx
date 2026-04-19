'use client';

/**
 * Aujasya — Consent Management Page
 * DPDPA 2023 compliant consent toggles with audit trail.
 */

import { useState, useEffect } from 'react';
import { useTranslations } from 'next-intl';
import { useParams, useRouter } from 'next/navigation';
import api from '@/lib/api-client';
import { BottomNav } from '@/components/bottom-nav';

interface ConsentRecord {
  purpose: string;
  granted: boolean;
  updated_at: string;
}

export default function ConsentPage() {
  const t = useTranslations('consent');
  const tCommon = useTranslations('common');
  const { locale } = useParams<{ locale: string }>();
  const router = useRouter();
  const [consents, setConsents] = useState<ConsentRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  const consentItems = [
    { purpose: 'essential', label: t('essential'), desc: t('essentialDesc'), required: true },
    { purpose: 'notifications', label: t('notifications'), desc: t('notificationsDesc'), required: false },
    { purpose: 'caregiver_sharing', label: t('caregiver'), desc: t('caregiverDesc'), required: false },
    { purpose: 'analytics', label: t('analytics'), desc: t('analyticsDesc'), required: false },
  ];

  useEffect(() => {
    const fetchConsents = async () => {
      try {
        const { data } = await api.get('/settings/consents');
        setConsents(data);
      } catch {
        // Initialize defaults
        setConsents(consentItems.map((c) => ({
          purpose: c.purpose,
          granted: c.required,
          updated_at: new Date().toISOString(),
        })));
      }
      setIsLoading(false);
    };
    fetchConsents();
  }, []);

  const toggleConsent = async (purpose: string) => {
    const item = consentItems.find((c) => c.purpose === purpose);
    if (item?.required) return; // Can't toggle essential

    const current = consents.find((c) => c.purpose === purpose);
    const newValue = !current?.granted;

    setIsSaving(true);
    try {
      await api.post('/settings/consents', {
        purpose,
        granted: newValue,
      });
      setConsents((prev) =>
        prev.map((c) =>
          c.purpose === purpose
            ? { ...c, granted: newValue, updated_at: new Date().toISOString() }
            : c
        )
      );
    } catch { /* silent */ }
    setIsSaving(false);
  };

  return (
    <div className="min-h-screen bg-background pb-24">
      <header className="border-b border-border bg-card px-4 pb-4 pt-safe">
        <div className="flex items-center gap-3 pt-4">
          <button onClick={() => router.back()} className="text-xl">←</button>
          <div>
            <h1 className="text-xl font-bold">{t('title')}</h1>
            <p className="text-sm text-muted-foreground">{t('subtitle')}</p>
          </div>
        </div>
      </header>

      <div className="px-4 pt-4 space-y-3">
        {isLoading ? (
          <div className="flex justify-center py-10">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          </div>
        ) : (
          consentItems.map((item) => {
            const consent = consents.find((c) => c.purpose === item.purpose);
            return (
              <div key={item.purpose} className="rounded-xl border border-border bg-card p-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <p className="font-medium">{item.label}</p>
                    <p className="mt-0.5 text-sm text-muted-foreground">{item.desc}</p>
                    {consent?.updated_at && (
                      <p className="mt-1 text-xs text-muted-foreground">
                        {t('lastUpdated', { date: new Date(consent.updated_at).toLocaleDateString() })}
                      </p>
                    )}
                  </div>
                  <button
                    onClick={() => toggleConsent(item.purpose)}
                    disabled={item.required || isSaving}
                    className={`relative h-7 w-12 rounded-full transition-colors ${
                      consent?.granted ? 'bg-primary' : 'bg-muted'
                    } ${item.required ? 'opacity-50 cursor-not-allowed' : ''}`}
                    role="switch"
                    aria-checked={consent?.granted}
                    aria-label={item.label}
                  >
                    <div
                      className={`absolute top-0.5 h-6 w-6 rounded-full bg-white shadow transition-transform ${
                        consent?.granted ? 'translate-x-5' : 'translate-x-0.5'
                      }`}
                    />
                  </button>
                </div>
                {item.required && (
                  <p className="mt-2 text-xs text-amber-600">{t('essential')} — required</p>
                )}
              </div>
            );
          })
        )}
      </div>

      <BottomNav locale={locale} />
    </div>
  );
}
