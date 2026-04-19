'use client';

/**
 * Aujasya — Settings Page
 * Profile, language, notifications, consent management, logout.
 */

import { useTranslations } from 'next-intl';
import { useParams, useRouter } from 'next/navigation';
import { useAuthStore } from '@/stores/auth-store';
import { BottomNav } from '@/components/bottom-nav';
import { localeNames, type Locale } from '@/i18n/config';

export default function SettingsPage() {
  const t = useTranslations('settings');
  const { locale } = useParams<{ locale: string }>();
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);

  const handleLogout = async () => {
    await logout();
    router.push(`/${locale}/login`);
  };

  const handleLogoutAll = async () => {
    await logout(true);
    router.push(`/${locale}/login`);
  };

  const switchLanguage = (newLocale: Locale) => {
    const path = window.location.pathname.replace(`/${locale}`, `/${newLocale}`);
    router.push(path);
  };

  const settingsSections = [
    {
      title: t('profile'),
      icon: '👤',
      description: user?.fullName || user?.phoneNumber || '',
      onClick: () => {},
    },
    {
      title: t('language'),
      icon: '🌐',
      description: localeNames[locale as Locale] || locale,
      onClick: () => {},
      extra: (
        <div className="mt-2 flex flex-wrap gap-2">
          {(Object.entries(localeNames) as [Locale, string][]).map(([code, name]) => (
            <button
              key={code}
              onClick={() => switchLanguage(code)}
              className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                locale === code
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted text-muted-foreground hover:bg-muted/80'
              }`}
            >
              {name}
            </button>
          ))}
        </div>
      ),
    },
    {
      title: t('notifications'),
      icon: '🔔',
      description: 'Push, SMS, WhatsApp',
      onClick: () => {},
    },
    {
      title: t('mealTimes'),
      icon: '🍽️',
      description: 'Breakfast, Lunch, Dinner',
      onClick: () => {},
    },
    {
      title: t('consent'),
      icon: '🔒',
      description: 'DPDPA 2023',
      onClick: () => {},
    },
  ];

  return (
    <div className="min-h-screen bg-background pb-24">
      <header className="border-b border-border bg-card px-4 pb-4 pt-safe">
        <h1 className="pt-4 text-2xl font-bold">{t('title')}</h1>
      </header>

      <div className="px-4 pt-4 space-y-2">
        {settingsSections.map((section) => (
          <div key={section.title}>
            <button
              onClick={section.onClick}
              className="w-full rounded-xl border border-border bg-card p-4 text-left transition-colors hover:bg-muted/50"
            >
              <div className="flex items-center gap-3">
                <span className="text-xl">{section.icon}</span>
                <div className="flex-1">
                  <p className="font-medium">{section.title}</p>
                  <p className="text-sm text-muted-foreground">{section.description}</p>
                </div>
                <span className="text-muted-foreground">›</span>
              </div>
            </button>
            {section.extra && <div className="px-4 pb-2">{section.extra}</div>}
          </div>
        ))}

        {/* Logout buttons */}
        <div className="pt-6 space-y-3">
          <button
            onClick={handleLogout}
            className="w-full rounded-xl border border-destructive/30 bg-card py-3.5 text-sm font-medium text-destructive transition-colors hover:bg-destructive/5"
          >
            {t('logout')}
          </button>
          <button
            onClick={handleLogoutAll}
            className="w-full rounded-xl border border-border bg-card py-3.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-muted/50"
          >
            {t('logoutAll')}
          </button>
        </div>

        <p className="text-center text-xs text-muted-foreground pt-4 pb-8">
          {t('version')} 1.0.0
        </p>
      </div>

      <BottomNav locale={locale} />
    </div>
  );
}
