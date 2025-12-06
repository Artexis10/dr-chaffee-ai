import { NextApiRequest, NextApiResponse } from 'next';
import { BACKEND_API_URL } from '../../../utils/env';

/**
 * Main App Logout - Proxies to backend to clear JWT cookies
 * 
 * The backend clears:
 * - access_token (JWT, HttpOnly)
 * - refresh_token (JWT, HttpOnly)
 * - Legacy auth_token and discord_user_id (for clean transition)
 * 
 * This endpoint does NOT clear tuning_auth - that's handled by /api/tuning/auth/logout.
 */
export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    // Proxy to backend unified auth logout
    const response = await fetch(`${BACKEND_API_URL}/api/auth/logout`, {
      method: 'POST',
      headers: {
        'Cookie': req.headers.cookie || '',
        'X-Requested-With': 'XMLHttpRequest', // CSRF protection
      },
    });

    // Forward Set-Cookie headers from backend (clears cookies)
    const setCookieHeader = response.headers.get('set-cookie');
    if (setCookieHeader) {
      res.setHeader('Set-Cookie', setCookieHeader);
    }

    // Parse response
    const data = await response.json();

    console.log('[Auth Logout] Main app logout successful');
    res.status(response.status).json(data);

  } catch (error) {
    console.error('[Auth Logout] Backend proxy error:', error);
    
    // Even if backend fails, clear cookies locally
    const isProduction = process.env.NODE_ENV === 'production';
    const cookiesToClear = [
      `access_token=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0${isProduction ? '; Secure' : ''}`,
      `refresh_token=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0${isProduction ? '; Secure' : ''}`,
      `auth_token=; Path=/; SameSite=Lax; Max-Age=0${isProduction ? '; Secure' : ''}`,
      `discord_user_id=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0${isProduction ? '; Secure' : ''}`,
    ];
    res.setHeader('Set-Cookie', cookiesToClear);
    
    res.status(200).json({ success: true, message: 'Logged out (local fallback)' });
  }
}
