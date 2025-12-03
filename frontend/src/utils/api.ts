/**
 * Centralized API Client
 * 
 * All API calls should go through this module to ensure:
 * - X-Session-ID header is included for log correlation
 * - Consistent error handling
 * - Credentials are included for auth cookies
 */

import { getSessionId } from './session';

export interface ApiOptions extends RequestInit {
  /** Skip adding session ID header (rarely needed) */
  skipSessionId?: boolean;
}

/**
 * Fetch wrapper that adds session ID and credentials to all requests.
 * 
 * @param url - API endpoint URL
 * @param options - Fetch options (method, body, headers, etc.)
 * @returns Response object
 * 
 * @example
 * const res = await apiFetch('/api/tuning/models');
 * const data = await res.json();
 * 
 * @example
 * const res = await apiFetch('/api/answer', {
 *   method: 'POST',
 *   body: JSON.stringify({ query: 'test' })
 * });
 */
export async function apiFetch(url: string, options: ApiOptions = {}): Promise<Response> {
  const { skipSessionId, headers: customHeaders, ...fetchOptions } = options;
  
  // Build headers
  const headers: HeadersInit = {
    ...customHeaders,
  };
  
  // Add session ID for log correlation
  if (!skipSessionId) {
    const sessionId = getSessionId();
    if (sessionId) {
      (headers as Record<string, string>)['X-Session-ID'] = sessionId;
    }
  }
  
  // Add Content-Type for JSON bodies
  if (fetchOptions.body && typeof fetchOptions.body === 'string') {
    try {
      JSON.parse(fetchOptions.body);
      (headers as Record<string, string>)['Content-Type'] = 'application/json';
    } catch {
      // Not JSON, don't add header
    }
  }
  
  return fetch(url, {
    ...fetchOptions,
    headers,
    credentials: 'include', // Always include cookies for auth
  });
}

/**
 * Convenience wrapper for GET requests that returns JSON.
 */
export async function apiGet<T = unknown>(url: string): Promise<T> {
  const res = await apiFetch(url);
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

/**
 * Convenience wrapper for POST requests that returns JSON.
 */
export async function apiPost<T = unknown>(url: string, body: unknown): Promise<T> {
  const res = await apiFetch(url, {
    method: 'POST',
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `API error: ${res.status}`);
  }
  return res.json();
}

/**
 * Convenience wrapper for PUT requests that returns JSON.
 */
export async function apiPut<T = unknown>(url: string, body: unknown): Promise<T> {
  const res = await apiFetch(url, {
    method: 'PUT',
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `API error: ${res.status}`);
  }
  return res.json();
}

/**
 * Convenience wrapper for DELETE requests.
 */
export async function apiDelete<T = unknown>(url: string): Promise<T> {
  const res = await apiFetch(url, {
    method: 'DELETE',
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `API error: ${res.status}`);
  }
  return res.json();
}
