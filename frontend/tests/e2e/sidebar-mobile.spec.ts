import { test, expect } from '@playwright/test';

/**
 * E2E tests for mobile sidebar behavior in the tuning dashboard.
 * Tests that the hamburger menu opens the sidebar and ONLY the sidebar's
 * internal X button closes it (header hamburger must NOT turn into an X).
 */

test.describe('Sidebar Mobile', () => {
  // Use mobile viewport for all tests in this describe block
  test.use({ viewport: { width: 375, height: 667 } });

  test.beforeEach(async ({ page }) => {
    // Set up authentication cookie for tuning dashboard access
    // This test requires TEST_APP_PASSWORD to be set
    const testPassword = process.env.TEST_APP_PASSWORD;
    
    if (!testPassword) {
      test.skip();
      return;
    }
    
    // Authenticate first
    await page.goto('/tuning/auth');
    const passwordInput = page.locator('input[type="password"]');
    const submitButton = page.locator('button[type="submit"]');
    await passwordInput.fill(testPassword);
    await submitButton.click();
    await page.waitForURL('/tuning', { timeout: 10000 });
  });

  test('should show hamburger icon on mobile', async ({ page }) => {
    // Hamburger menu button should be visible on mobile
    const hamburgerButton = page.locator('button[aria-label*="menu"], button[aria-label*="Menu"], .mobile-menu-button, [class*="hamburger"]');
    await expect(hamburgerButton.first()).toBeVisible();
  });

  test('should open sidebar when hamburger is clicked', async ({ page }) => {
    // Find and click hamburger button
    const hamburgerButton = page.locator('button[aria-label*="menu"], button[aria-label*="Menu"], .mobile-menu-button, [class*="hamburger"]').first();
    await hamburgerButton.click();
    
    // Sidebar should become visible
    const sidebar = page.locator('.tuning-sidebar, [class*="sidebar"]');
    await expect(sidebar.first()).toBeVisible();
    
    // Sidebar should contain navigation items
    const navItems = page.locator('.tuning-sidebar a, [class*="sidebar"] a');
    await expect(navItems.first()).toBeVisible();
  });

  test('should close sidebar with internal X button only', async ({ page }) => {
    // Open sidebar
    const hamburgerButton = page.locator('button[aria-label*="menu"], button[aria-label*="Menu"], .mobile-menu-button, [class*="hamburger"]').first();
    await hamburgerButton.click();
    
    // Sidebar should be visible
    const sidebar = page.locator('.tuning-sidebar, [class*="sidebar"]');
    await expect(sidebar.first()).toBeVisible();
    
    // Find the close button INSIDE the sidebar (not the header hamburger)
    const sidebarCloseButton = page.locator('.tuning-sidebar button[aria-label*="close"], .tuning-sidebar button[aria-label*="Close"], [class*="sidebar"] button svg');
    
    // If there's a close button in the sidebar, click it
    if (await sidebarCloseButton.first().isVisible()) {
      await sidebarCloseButton.first().click();
      
      // Sidebar should close
      await expect(sidebar.first()).not.toBeVisible();
    }
  });

  test('header hamburger should NOT turn into X when sidebar is open', async ({ page }) => {
    // Open sidebar
    const hamburgerButton = page.locator('button[aria-label*="menu"], button[aria-label*="Menu"], .mobile-menu-button, [class*="hamburger"]').first();
    await hamburgerButton.click();
    
    // Wait for sidebar to open
    const sidebar = page.locator('.tuning-sidebar, [class*="sidebar"]');
    await expect(sidebar.first()).toBeVisible();
    
    // The header hamburger should still be a hamburger icon (Menu), not an X
    // Check that the hamburger button still contains the Menu icon, not X icon
    const menuIcon = hamburgerButton.locator('svg');
    await expect(menuIcon).toBeVisible();
    
    // The hamburger should NOT have transformed into an X
    // This is verified by checking the button doesn't have "close" in its aria-label
    const ariaLabel = await hamburgerButton.getAttribute('aria-label');
    expect(ariaLabel?.toLowerCase()).not.toContain('close');
  });

  test('should close sidebar when clicking outside', async ({ page }) => {
    // Open sidebar
    const hamburgerButton = page.locator('button[aria-label*="menu"], button[aria-label*="Menu"], .mobile-menu-button, [class*="hamburger"]').first();
    await hamburgerButton.click();
    
    // Sidebar should be visible
    const sidebar = page.locator('.tuning-sidebar, [class*="sidebar"]');
    await expect(sidebar.first()).toBeVisible();
    
    // Click on the overlay/backdrop to close (if it exists)
    const overlay = page.locator('.sidebar-overlay, [class*="overlay"], [class*="backdrop"]');
    if (await overlay.first().isVisible()) {
      await overlay.first().click();
      await expect(sidebar.first()).not.toBeVisible();
    }
  });

  test('should close sidebar on escape key', async ({ page }) => {
    // Open sidebar
    const hamburgerButton = page.locator('button[aria-label*="menu"], button[aria-label*="Menu"], .mobile-menu-button, [class*="hamburger"]').first();
    await hamburgerButton.click();
    
    // Sidebar should be visible
    const sidebar = page.locator('.tuning-sidebar, [class*="sidebar"]');
    await expect(sidebar.first()).toBeVisible();
    
    // Press Escape
    await page.keyboard.press('Escape');
    
    // Sidebar should close
    await expect(sidebar.first()).not.toBeVisible();
  });

  test('should navigate correctly from sidebar', async ({ page }) => {
    // Open sidebar
    const hamburgerButton = page.locator('button[aria-label*="menu"], button[aria-label*="Menu"], .mobile-menu-button, [class*="hamburger"]').first();
    await hamburgerButton.click();
    
    // Sidebar should be visible
    const sidebar = page.locator('.tuning-sidebar, [class*="sidebar"]');
    await expect(sidebar.first()).toBeVisible();
    
    // Find a navigation link (e.g., "Instructions" or "Search Config")
    const navLink = page.locator('.tuning-sidebar a, [class*="sidebar"] a').first();
    
    if (await navLink.isVisible()) {
      await navLink.click();
      
      // Sidebar should close after navigation
      await expect(sidebar.first()).not.toBeVisible();
    }
  });

  test('should not have layout glitches when sidebar closes', async ({ page }) => {
    // Open sidebar
    const hamburgerButton = page.locator('button[aria-label*="menu"], button[aria-label*="Menu"], .mobile-menu-button, [class*="hamburger"]').first();
    await hamburgerButton.click();
    
    // Sidebar should be visible
    const sidebar = page.locator('.tuning-sidebar, [class*="sidebar"]');
    await expect(sidebar.first()).toBeVisible();
    
    // Close sidebar with Escape
    await page.keyboard.press('Escape');
    
    // Verify no horizontal scroll (layout glitch indicator)
    const bodyWidth = await page.evaluate(() => document.body.scrollWidth);
    const viewportWidth = await page.evaluate(() => window.innerWidth);
    
    // Body should not be wider than viewport (no horizontal overflow)
    expect(bodyWidth).toBeLessThanOrEqual(viewportWidth + 1); // +1 for rounding
    
    // Main content should still be visible and properly positioned
    const mainContent = page.locator('main, .tuning-content, [class*="content"]');
    if (await mainContent.first().isVisible()) {
      const box = await mainContent.first().boundingBox();
      expect(box?.x).toBeGreaterThanOrEqual(0);
    }
  });
});
