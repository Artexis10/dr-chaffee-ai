import { test, expect } from '@playwright/test';

/**
 * E2E tests for the tuning dashboard authentication flow.
 */

test.describe('Tuning Auth', () => {
  test('should load auth page correctly', async ({ page }) => {
    await page.goto('/tuning/auth');
    
    // Page title should be visible
    const title = page.locator('h1', { hasText: 'Tuning Dashboard' });
    await expect(title).toBeVisible();
    
    // Subtitle should be visible
    const subtitle = page.locator('p', { hasText: 'QA & Admin Access Only' });
    await expect(subtitle).toBeVisible();
    
    // Password input should be visible
    const passwordInput = page.locator('input[type="password"]');
    await expect(passwordInput).toBeVisible();
    
    // Submit button should be visible
    const submitButton = page.locator('button[type="submit"]');
    await expect(submitButton).toBeVisible();
    await expect(submitButton).toContainText('Access Dashboard');
  });

  test('should show error state for wrong password', async ({ page }) => {
    await page.goto('/tuning/auth');
    
    const passwordInput = page.locator('input[type="password"]');
    const submitButton = page.locator('button[type="submit"]');
    
    // Enter wrong password
    await passwordInput.fill('wrong_password_123');
    await submitButton.click();
    
    // Should show loading state
    await expect(submitButton).toContainText('Unlocking...');
    
    // Should show error message (wait for API response)
    const errorMessage = page.locator('.tuning-auth-error');
    await expect(errorMessage).toBeVisible({ timeout: 10000 });
    await expect(errorMessage).toContainText('Incorrect password');
    
    // Password input should be cleared
    await expect(passwordInput).toHaveValue('');
    
    // Input should have error styling
    await expect(passwordInput).toHaveClass(/error/);
  });

  test('should redirect to dashboard on correct password', async ({ page }) => {
    // This test requires the correct password to be set in environment
    // Skip if APP_PASSWORD is not configured for testing
    const testPassword = process.env.TEST_APP_PASSWORD;
    
    if (!testPassword) {
      test.skip();
      return;
    }
    
    await page.goto('/tuning/auth');
    
    const passwordInput = page.locator('input[type="password"]');
    const submitButton = page.locator('button[type="submit"]');
    
    // Enter correct password
    await passwordInput.fill(testPassword);
    await submitButton.click();
    
    // Should redirect to tuning dashboard
    await page.waitForURL('/tuning', { timeout: 10000 });
    
    // Dashboard should load
    const dashboardContent = page.locator('.tuning-dashboard, .tuning-page');
    await expect(dashboardContent.first()).toBeVisible({ timeout: 10000 });
  });

  test('should have back link to main app', async ({ page }) => {
    await page.goto('/tuning/auth');
    
    // Back link should be visible
    const backLink = page.locator('a', { hasText: 'Back to Main App' });
    await expect(backLink).toBeVisible();
    await expect(backLink).toHaveAttribute('href', '/');
  });

  test('should show avatar image', async ({ page }) => {
    await page.goto('/tuning/auth');
    
    // Avatar image should be visible
    const avatar = page.locator('.tuning-auth-avatar img');
    await expect(avatar).toBeVisible();
  });

  test('should show security notice', async ({ page }) => {
    await page.goto('/tuning/auth');
    
    // Security notice should be visible
    const notice = page.locator('.tuning-auth-notice');
    await expect(notice).toBeVisible();
    await expect(notice).toContainText('privileged users only');
  });
});

test.describe('Tuning Auth - Redirect', () => {
  test('should redirect unauthenticated users to auth page', async ({ page }) => {
    // Try to access protected tuning page directly
    await page.goto('/tuning');
    
    // Should redirect to auth page
    await page.waitForURL(/\/tuning\/auth/, { timeout: 10000 });
    
    // Auth page should be visible
    const title = page.locator('h1', { hasText: 'Tuning Dashboard' });
    await expect(title).toBeVisible();
  });
});
