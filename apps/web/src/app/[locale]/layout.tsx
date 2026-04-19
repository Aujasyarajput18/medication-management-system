/**
 * Aujasya — Locale Layout
 * Wraps all locale pages with next-intl provider and auth initialization.
 *
 * [Issue #5] ClientAuthInit is rendered HERE in the root locale layout,
 * NOT in any individual page. This ensures that on ANY direct URL navigation
 * (/today, /medicines, /calendar, etc.), the auth store calls initializeAuth()
 * BEFORE any child page component mounts and fires API calls.
 *
 * Without this, navigating directly to /today would render the page without
 * an access token, fire all API calls unauthenticated, get 401s, and redirect
 * to login — even if the user has a valid refresh token cookie.
 */

import { NextIntlClientProvider } from 'next-intl';
import { getMessages } from 'next-intl/server';
import { notFound } from 'next/navigation';
import { locales, type Locale } from '@/i18n/config';
import { ClientAuthInit } from '@/components/client-auth-init';
import { OnlineStatusProvider } from '@/components/online-status-provider';

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}

export default async function LocaleLayout({
  children,
  params: { locale },
}: {
  children: React.ReactNode;
  params: { locale: string };
}) {
  if (!locales.includes(locale as Locale)) {
    notFound();
  }

  const messages = await getMessages();

  return (
    <html lang={locale} dir="ltr">
      <head>
        <link rel="apple-touch-icon" href="/icons/icon-192.png" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
      </head>
      <body className="min-h-screen bg-background font-sans antialiased">
        <NextIntlClientProvider messages={messages}>
          {/* 
            [Issue #5] Auth initialization runs at the layout level.
            ClientAuthInit calls initializeAuth() once on mount via useEffect.
            This is a client component — it renders null (no UI output).
            It MUST be here, not in individual pages.
          */}
          <ClientAuthInit />
          {/* 
            [FIX-8] OnlineStatusProvider listens for online/offline events
            and triggers sync on reconnect. Must be layout-level to persist
            across page navigations.
          */}
          <OnlineStatusProvider />
          <main className="pb-safe">{children}</main>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
