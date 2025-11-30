import { test, expect, Page } from '@playwright/test';

/**
 * E2E tests for the main search functionality on the homepage.
 * Tests both desktop and mobile viewports.
 */

/**
 * Helper to wait for the main app to load (handles password gate).
 * If password gate is shown, it waits for it to resolve.
 * If no password is required, the app loads directly.
 */
async function waitForAppLoad(page: Page) {
  // Wait for either the search input (app loaded) or password gate to appear
  const searchInput = page.locator('input[aria-label="Search query"]');
  const passwordGate = page.locator('text=Enter password');
  const loadingText = page.locator('text=Loading...');
  
  // Wait for loading to finish
  await expect(loadingText).toBeHidden({ timeout: 10000 }).catch(() => {});
  
  // Check if password gate is shown
  const isPasswordGateVisible = await passwordGate.isVisible().catch(() => false);
  
  if (isPasswordGateVisible) {
    // Skip test if password is required (can't test without credentials)
    test.skip(true, 'Password gate is enabled - skipping main search tests');
    return;
  }
  
  // Wait for search input to be visible
  await expect(searchInput).toBeVisible({ timeout: 15000 });
}

test.describe('Main Search', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await waitForAppLoad(page);
  });

  test('should display search input and button', async ({ page }) => {
    // Search input should be visible
    const searchInput = page.locator('input[aria-label="Search query"]');
    await expect(searchInput).toBeVisible();
    
    // Search button should be visible
    const searchButton = page.locator('button[type="submit"]');
    await expect(searchButton).toBeVisible();
    await expect(searchButton).toContainText('Search');
  });

  test('should allow typing in search field', async ({ page }) => {
    const searchInput = page.locator('input[aria-label="Search query"]');
    
    await searchInput.fill('What does Dr Chaffee say about carnivore diet?');
    await expect(searchInput).toHaveValue('What does Dr Chaffee say about carnivore diet?');
  });

  test('should submit search and display response container', async ({ page }) => {
    const searchInput = page.locator('input[aria-label="Search query"]');
    const searchButton = page.locator('button[type="submit"]');
    
    // Type a query
    await searchInput.fill('carnivore diet benefits');
    
    // Click search
    await searchButton.click();
    
    // Button should show loading state
    await expect(searchButton).toContainText('Searching...');
    
    // Wait for response container to appear (with generous timeout for API call)
    // The answer card or loading skeleton should appear
    const responseContainer = page.locator('.answer-card, .loading-skeleton, [class*="answer"]');
    await expect(responseContainer.first()).toBeVisible({ timeout: 60000 });
  });

  test('should show answer style toggle (Short/Long)', async ({ page }) => {
    // Answer style toggle should be visible
    const shortButton = page.locator('button.toggle-btn', { hasText: 'Short' });
    const longButton = page.locator('button.toggle-btn', { hasText: 'Long' });
    
    await expect(shortButton).toBeVisible();
    await expect(longButton).toBeVisible();
    
    // Short should be active by default
    await expect(shortButton).toHaveClass(/active/);
  });

  test('should show source filter pills', async ({ page }) => {
    // Source filter pills should be visible
    const allPill = page.locator('button.filter-pill', { hasText: 'All' });
    const youtubePill = page.locator('button.filter-pill', { hasText: 'YouTube' });
    const zoomPill = page.locator('button.filter-pill', { hasText: 'Zoom' });
    
    await expect(allPill).toBeVisible();
    await expect(youtubePill).toBeVisible();
    await expect(zoomPill).toBeVisible();
    
    // All should be active by default
    await expect(allPill).toHaveClass(/active/);
  });

  test('should clear search input with clear button', async ({ page }) => {
    const searchInput = page.locator('input[aria-label="Search query"]');
    
    // Type something
    await searchInput.fill('test query');
    await expect(searchInput).toHaveValue('test query');
    
    // Clear button should appear
    const clearButton = page.locator('button[aria-label="Clear search"]');
    await expect(clearButton).toBeVisible();
    
    // Click clear
    await clearButton.click();
    
    // Input should be empty
    await expect(searchInput).toHaveValue('');
  });

  test('should submit search on Enter key', async ({ page }) => {
    const searchInput = page.locator('input[aria-label="Search query"]');
    const searchButton = page.locator('button[type="submit"]');
    
    // Type a query
    await searchInput.fill('carnivore diet');
    
    // Press Enter
    await searchInput.press('Enter');
    
    // Button should show loading state
    await expect(searchButton).toContainText('Searching...');
  });
});

test.describe('Main Search - Mobile', () => {
  test.use({ viewport: { width: 375, height: 667 } });

  test('should work on mobile viewport', async ({ page }) => {
    await page.goto('/');
    await waitForAppLoad(page);
    
    // Search input should be visible
    const searchInput = page.locator('input[aria-label="Search query"]');
    await expect(searchInput).toBeVisible();
    
    // Search button should be visible
    const searchButton = page.locator('button[type="submit"]');
    await expect(searchButton).toBeVisible();
    
    // Type and search
    await searchInput.fill('test mobile search');
    await searchButton.click();
    
    // Should show loading state
    await expect(searchButton).toContainText('Searching...');
  });

  test('should display filter pills on mobile', async ({ page }) => {
    await page.goto('/');
    await waitForAppLoad(page);
    
    // Filter pills should be visible and accessible
    const allPill = page.locator('button.filter-pill', { hasText: 'All' });
    await expect(allPill).toBeVisible();
  });
});
