import { NextApiRequest, NextApiResponse } from 'next';
import { BACKEND_API_URL } from '../../../../utils/env';

/**
 * Discord User Info Proxy - Fetches current user info from backend
 * 
 * Proxies the request to backend /auth/discord/me endpoint,
 * forwarding cookies for authentication.
 */

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    // Forward cookies to backend
    const cookieHeader = req.headers.cookie || '';
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);
    
    const response = await fetch(`${BACKEND_API_URL}/auth/discord/me`, {
      headers: {
        'Cookie': cookieHeader,
      },
      signal: controller.signal,
    });
    
    clearTimeout(timeoutId);
    
    if (response.ok) {
      const data = await response.json();
      return res.status(200).json(data);
    } else if (response.status === 401) {
      return res.status(401).json({ authenticated: false, error: 'Not authenticated' });
    } else {
      console.error('[Discord Me] Backend error:', response.status);
      return res.status(response.status).json({ error: 'Backend error' });
    }
  } catch (error) {
    console.error('[Discord Me] Error fetching user info:', error);
    return res.status(500).json({ error: 'Failed to fetch user info' });
  }
}
