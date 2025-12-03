/**
 * Session ID Management
 * 
 * Generates and persists a stable session ID for log correlation.
 * The session ID is sent with all API requests via X-Session-ID header.
 */

const SESSION_ID_KEY = 'askdrchaffee.session_id';

/**
 * Generate a UUID v4-style session ID.
 */
function generateSessionId(): string {
  // Use crypto.randomUUID if available (modern browsers)
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID().slice(0, 8); // Short ID for readability
  }
  
  // Fallback for older browsers
  return 'xxxxxxxx'.replace(/[x]/g, () => {
    return Math.floor(Math.random() * 16).toString(16);
  });
}

/**
 * Get the current session ID, creating one if it doesn't exist.
 * 
 * The session ID persists in localStorage across page reloads
 * but is unique per browser/device.
 */
export function getSessionId(): string {
  if (typeof window === 'undefined') {
    // SSR - return empty string
    return '';
  }
  
  let sessionId = localStorage.getItem(SESSION_ID_KEY);
  
  if (!sessionId) {
    sessionId = generateSessionId();
    localStorage.setItem(SESSION_ID_KEY, sessionId);
  }
  
  return sessionId;
}

/**
 * Clear the session ID (useful for logout).
 */
export function clearSessionId(): void {
  if (typeof window !== 'undefined') {
    localStorage.removeItem(SESSION_ID_KEY);
  }
}
