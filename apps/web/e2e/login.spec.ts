/**
 * Aujasya — E2E: Login Journey
 * Tests the complete OTP login flow.
 */

import { test, expect } from '@playwright/test';

test.describe('Login Journey', () => {
  test('should show login page with phone input', async ({ page }) => {
    await page.goto('/hi/login');

    // Title visible
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();

    // Phone input present
    const phoneInput = page.getByRole('textbox', { name: /mobile/i });
    await expect(phoneInput).toBeVisible();
    await expect(phoneInput).toHaveValue('+91');
  });

  test('should validate Indian phone number', async ({ page }) => {
    await page.goto('/hi/login');

    const phoneInput = page.getByRole('textbox', { name: /mobile/i });
    const submitBtn = page.getByRole('button', { name: /otp/i });

    // Invalid number — button should be disabled
    await phoneInput.fill('+1234567890');
    await expect(submitBtn).toBeDisabled();

    // Valid number — button should be enabled
    await phoneInput.fill('+919876543210');
    await expect(submitBtn).toBeEnabled();
  });

  test('should redirect unauthenticated users to login', async ({ page }) => {
    await page.goto('/hi/today');

    // Should redirect to login
    await expect(page).toHaveURL(/\/login/);
  });
});
