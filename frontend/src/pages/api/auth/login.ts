import { NextApiRequest, NextApiResponse } from 'next';
import { BACKEND_API_URL } from '../../../utils/env';

/**
 * Login endpoint - Proxies to backend for unified JWT auth
 * 
 * The backend validates APP_PASSWORD and issues JWT access + refresh tokens
 * as HttpOnly cookies. Tokens are NEVER returned in the response body.
 * 
 * Required env vars (on backend):
 * - APP_PASSWORD: The password users must enter to access the app
 * - AUTH_SESSION_SECRET: Secret for signing JWTs (required in production)
 */
export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { password } = req.body;

  if (!password) {
    return res.status(400).json({ error: 'Password required' });
  }

  console.log('[Auth Login] Password attempt received, proxying to backend');

  try {
    // Proxy to backend unified auth endpoint
    const response = await fetch(`${BACKEND_API_URL}/api/auth/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest', // CSRF protection
      },
      body: JSON.stringify({ password }),
    });

    // Forward Set-Cookie headers from backend (contains JWT tokens)
    const setCookieHeader = response.headers.get('set-cookie');
    if (setCookieHeader) {
      res.setHeader('Set-Cookie', setCookieHeader);
    }

    // Parse response
    const data = await response.json();

    // Return with same status code
    // NOTE: Tokens are in cookies, NOT in response body
    res.status(response.status).json(data);

  } catch (error) {
    console.error('[Auth Login] Backend proxy error:', error);
    res.status(503).json({ error: 'Authentication service unavailable' });
  }
}
