/**
 * Aujasya — i18n Configuration
 * Supports 6 languages (Hindi default).
 */

export const locales = ['hi', 'en', 'ta', 'te', 'bn', 'mr'] as const;
export type Locale = (typeof locales)[number];
export const defaultLocale: Locale = 'hi';

export const localeNames: Record<Locale, string> = {
  hi: 'हिंदी',
  en: 'English',
  ta: 'தமிழ்',
  te: 'తెలుగు',
  bn: 'বাংলা',
  mr: 'मराठी',
};
