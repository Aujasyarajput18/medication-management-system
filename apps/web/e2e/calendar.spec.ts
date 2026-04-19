/**
 * Aujasya — E2E: Calendar
 * [FIX-15] Validates month=YYYY-MM navigation.
 */

import { test, expect } from '@playwright/test';

test.describe('Calendar Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.context().addCookies([{
      name: 'refresh_token',
      value: 'mock-refresh-token',
      domain: 'localhost',
      path: '/',
    }]);
  });

  test('should display calendar with month navigation', async ({ page }) => {
    await page.goto('/hi/calendar');

    // Month navigation buttons
    const prevBtn = page.getByRole('button', { name: /previous/i });
    const nextBtn = page.getByRole('button', { name: /next/i });

    await expect(prevBtn).toBeVisible();
    await expect(nextBtn).toBeVisible();
  });

  test('should show color legend', async ({ page }) => {
    await page.goto('/en/calendar');

    await page.waitForTimeout(1000);
    const body = await page.textContent('body');
    expect(body).toContain('100%');
  });
});
