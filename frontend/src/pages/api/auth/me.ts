import { NextApiRequest, NextApiResponse } from 'next';
import { BACKEND_API_URL } from '../../../utils/env';

/**
 * Auth Me Proxy - Get current user with automatic token refresh
 * 
 * Proxies to backend /api/auth/me which:
 * 1. If access_token valid → returns user info
 * 2. If access_token expired but refresh_token valid → mints new tokens, returns user
 * 3. If both invalid → returns 401
 * 
 * Security:
 * - Forwards HttpOnly cookies to backend
 * - Backend sets new cookies if tokens are refreshed
 * - Tokens never appear in response body
 */
export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
): Promise<void> {
  if (req.method !== 'GET') {
    res.status(405).json({ error: 'Method not allowed' });
    return;
  }

  try {
    // Forward request to backend with cookies
    const response = await fetch(`${BACKEND_API_URL}/api/auth/me`, {
      method: 'GET',
      headers: {
        'Cookie': req.headers.cookie || '',
        'X-Requested-With': 'XMLHttpRequest', // CSRF protection
      },
    });

    // Forward any Set-Cookie headers from backend (for token refresh)
    const setCookieHeader = response.headers.get('set-cookie');
    if (setCookieHeader) {
      res.setHeader('Set-Cookie', setCookieHeader);
    }

    // Parse response
    const data = await response.json();

    // Return with same status code
    res.status(response.status).json(data);

  } catch (error) {
    console.error('[Auth Me] Proxy error:', error);
    res.status(503).json({
      authenticated: false,
      detail: 'auth_service_unavailable',
    });
  }
}
