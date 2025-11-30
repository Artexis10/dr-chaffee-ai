/**
 * Shared test utilities for E2E and component tests.
 */

/**
 * Wait for a specific amount of time.
 * Use sparingly - prefer waiting for specific conditions.
 */
export const wait = (ms: number): Promise<void> => 
  new Promise(resolve => setTimeout(resolve, ms));

/**
 * Generate a random test query for search tests.
 */
export const generateTestQuery = (): string => {
  const topics = [
    'carnivore diet',
    'meat only diet',
    'autoimmune disease',
    'metabolic health',
    'protein intake',
    'animal based nutrition'
  ];
  return topics[Math.floor(Math.random() * topics.length)];
};

/**
 * Mobile viewport dimensions for testing.
 */
export const MOBILE_VIEWPORT = {
  width: 375,
  height: 667
};

/**
 * Tablet viewport dimensions for testing.
 */
export const TABLET_VIEWPORT = {
  width: 768,
  height: 1024
};

/**
 * Desktop viewport dimensions for testing.
 */
export const DESKTOP_VIEWPORT = {
  width: 1280,
  height: 720
};
