/**
 * Aujasya — E2E: PWA Install & Offline
 */

import { test, expect } from '@playwright/test';

test.describe('PWA Features', () => {
  test('should serve manifest.json', async ({ page }) => {
    const response = await page.goto('/manifest.json');
    expect(response?.status()).toBe(200);

    const manifest = await response?.json();
    expect(manifest.name).toBe('Aujasya — औजस्य');
    expect(manifest.display).toBe('standalone');
    expect(manifest.start_url).toBe('/hi/today');
  });

  test('should serve offline.html', async ({ page }) => {
    const response = await page.goto('/offline.html');
    expect(response?.status()).toBe(200);

    const content = await page.textContent('body');
    expect(content).toContain('offline');
  });

  test('should have PWA icons', async ({ page }) => {
    const icon192 = await page.goto('/icons/icon-192.png');
    expect(icon192?.status()).toBe(200);

    const icon512 = await page.goto('/icons/icon-512.png');
    expect(icon512?.status()).toBe(200);
  });
});
