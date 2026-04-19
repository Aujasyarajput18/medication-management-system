/**
 * Aujasya — i18n Tests
 * Validates all 6 translation files have the same keys.
 */

import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

const messagesDir = path.join(process.cwd(), 'src/messages');
const locales = ['hi', 'en', 'ta', 'te', 'bn', 'mr'];

function getAllKeys(obj: any, prefix = ''): string[] {
  const keys: string[] = [];
  for (const [key, value] of Object.entries(obj)) {
    const fullKey = prefix ? `${prefix}.${key}` : key;
    if (typeof value === 'object' && value !== null) {
      keys.push(...getAllKeys(value, fullKey));
    } else {
      keys.push(fullKey);
    }
  }
  return keys.sort();
}

describe('i18n Translation Files', () => {
  const translations: Record<string, any> = {};

  for (const locale of locales) {
    const filePath = path.join(messagesDir, `${locale}.json`);
    it(`should have a valid ${locale}.json file`, () => {
      expect(fs.existsSync(filePath)).toBe(true);
      const content = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
      translations[locale] = content;
      expect(content).toBeDefined();
      expect(typeof content).toBe('object');
    });
  }

  it('should have matching keys across all locales', () => {
    const enKeys = getAllKeys(translations['en'] || {});

    for (const locale of locales) {
      if (locale === 'en') continue;
      const localeKeys = getAllKeys(translations[locale] || {});

      const missingInLocale = enKeys.filter((k) => !localeKeys.includes(k));
      const extraInLocale = localeKeys.filter((k) => !enKeys.includes(k));

      expect(
        missingInLocale,
        `${locale} is missing keys: ${missingInLocale.join(', ')}`
      ).toEqual([]);
      expect(
        extraInLocale,
        `${locale} has extra keys: ${extraInLocale.join(', ')}`
      ).toEqual([]);
    }
  });
});
