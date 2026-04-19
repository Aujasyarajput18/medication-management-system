/**
 * Aujasya — next-intl Request Configuration
 */

import { getRequestConfig } from 'next-intl/server';
import { locales, defaultLocale, type Locale } from './config';

export default getRequestConfig(async ({ locale }) => {
  const validLocale = locales.includes(locale as Locale)
    ? (locale as Locale)
    : defaultLocale;

  return {
    messages: (await import(`../messages/${validLocale}.json`)).default,
  };
});
