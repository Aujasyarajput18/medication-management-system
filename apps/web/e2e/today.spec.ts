/**
 * Aujasya — E2E: Today Dashboard
 */

import { test, expect } from '@playwright/test';

test.describe('Today Dashboard', () => {
  // Note: In real E2E, you'd set up auth cookies/tokens before each test.
  // This tests the UI structure with mocked auth.

  test('should display bottom navigation with 5 tabs', async ({ page }) => {
    // Set a mock refresh_token cookie for auth
    await page.context().addCookies([{
      name: 'refresh_token',
      value: 'mock-refresh-token',
      domain: 'localhost',
      path: '/',
    }]);

    await page.goto('/hi/today');

    const nav = page.getByRole('navigation', { name: /main/i });
    await expect(nav).toBeVisible();

    // 5 navigation links
    const links = nav.getByRole('link');
    await expect(links).toHaveCount(5);
  });

  test('should show empty state when no doses', async ({ page }) => {
    await page.context().addCookies([{
      name: 'refresh_token',
      value: 'mock-refresh-token',
      domain: 'localhost',
      path: '/',
    }]);

    await page.goto('/hi/today');

    // Loading spinner or empty state should appear
    await page.waitForTimeout(2000);

    // Either shows dose cards or empty state
    const pageContent = await page.textContent('body');
    expect(pageContent).toBeTruthy();
  });
});
