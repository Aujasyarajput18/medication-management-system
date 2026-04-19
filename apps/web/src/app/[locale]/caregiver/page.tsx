'use client';

/**
 * Aujasya — Caregiver Page
 * For patients: invite caregivers, manage links.
 * For caregivers: view patient summaries.
 */

import { useState, useEffect } from 'react';
import { useTranslations } from 'next-intl';
import { useParams } from 'next/navigation';
import { useAuthStore } from '@/stores/auth-store';
import { BottomNav } from '@/components/bottom-nav';
import api from '@/lib/api-client';

interface PatientSummary {
  patient_id: string;
  name: string | null;
  adherence_today_pct: number;
  total_doses_today: number;
  taken_doses_today: number;
  current_streak: number;
  has_overdue: boolean;
}

export default function CaregiverPage() {
  const t = useTranslations('caregiver');
  const { locale } = useParams<{ locale: string }>();
  const user = useAuthStore((s) => s.user);
  const isCaregiver = user?.role === 'caregiver';

  const [patients, setPatients] = useState<PatientSummary[]>([]);
  const [phone, setPhone] = useState('+91');
  const [inviteError, setInviteError] = useState('');
  const [inviteSuccess, setInviteSuccess] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (isCaregiver) {
      fetchPatients();
    }
  }, [isCaregiver]);

  const fetchPatients = async () => {
    setIsLoading(true);
    try {
      const { data } = await api.get('/caregivers/patients');
      setPatients(data);
    } catch { /* empty */ }
    setIsLoading(false);
  };

  const handleInvite = async (e: React.FormEvent) => {
    e.preventDefault();
    setInviteError('');
    setInviteSuccess(false);

    try {
      await api.post('/caregivers/invite', { caregiver_phone: phone });
      setInviteSuccess(true);
      setPhone('+91');
    } catch (err: any) {
      setInviteError(err.response?.data?.detail || 'Failed to send invitation');
    }
  };

  return (
    <div className="min-h-screen bg-background pb-24">
      <header className="border-b border-border bg-card px-4 pb-4 pt-safe">
        <h1 className="pt-4 text-2xl font-bold">{t('title')}</h1>
      </header>

      <div className="px-4 pt-4">
        {isCaregiver ? (
          /* Caregiver View: Patient Dashboard */
          <div>
            <h2 className="text-lg font-semibold mb-4">{t('patientDashboard')}</h2>
            {isLoading ? (
              <div className="flex justify-center py-10">
                <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
              </div>
            ) : patients.length === 0 ? (
              <p className="text-center py-10 text-muted-foreground">{t('noPatients')}</p>
            ) : (
              <div className="space-y-3">
                {patients.map((p) => (
                  <div key={p.patient_id} className="rounded-xl border bg-card p-4 shadow-sm">
                    <div className="flex items-start justify-between">
                      <div>
                        <h3 className="font-semibold">{p.name || 'Patient'}</h3>
                        <p className="text-sm text-muted-foreground mt-1">
                          {t('adherenceToday')}: {p.adherence_today_pct}%
                        </p>
                        <p className="text-sm text-muted-foreground">
                          {p.taken_doses_today}/{p.total_doses_today} doses · {p.current_streak} day streak
                        </p>
                      </div>
                      {p.has_overdue && (
                        <span className="rounded-full bg-red-100 px-2.5 py-1 text-xs font-medium text-red-700">
                          {t('overdueAlert')}
                        </span>
                      )}
                    </div>
                    {/* Mini progress bar */}
                    <div className="mt-3 h-2 rounded-full bg-muted">
                      <div
                        className={cn(
                          'h-full rounded-full transition-all',
                          p.adherence_today_pct >= 80 ? 'bg-green-500' : p.adherence_today_pct >= 50 ? 'bg-amber-500' : 'bg-red-500'
                        )}
                        style={{ width: `${p.adherence_today_pct}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : (
          /* Patient View: Invite Caregiver */
          <div>
            <h2 className="text-lg font-semibold">{t('inviteTitle')}</h2>
            <p className="text-sm text-muted-foreground mt-1">{t('inviteSubtitle')}</p>

            <form onSubmit={handleInvite} className="mt-4 space-y-3">
              <input
                type="tel"
                inputMode="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder={t('phoneLabel')}
                className="w-full rounded-xl border border-input bg-background px-4 py-3 text-sm focus:border-primary focus:outline-none focus:ring-2 focus:ring-ring"
                maxLength={13}
              />

              {inviteError && (
                <p className="text-sm text-destructive">{inviteError}</p>
              )}
              {inviteSuccess && (
                <p className="text-sm text-green-600">✅ Invitation sent successfully!</p>
              )}

              <button
                type="submit"
                disabled={!/^\+91[6-9]\d{9}$/.test(phone)}
                className="w-full rounded-xl bg-primary py-3 text-sm font-semibold text-primary-foreground disabled:opacity-50"
              >
                {t('invite')}
              </button>
            </form>
          </div>
        )}
      </div>

      <BottomNav locale={locale} />
    </div>
  );
}

import { cn } from '@/lib/utils';
