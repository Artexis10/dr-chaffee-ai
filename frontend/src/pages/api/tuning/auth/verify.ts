import { NextApiRequest, NextApiResponse } from 'next';

/**
 * Tuning Auth Verify - Proxy to backend tuning authentication
 * 
 * Flow:
 * 1. Frontend sends password to this proxy
 * 2. Proxy forwards to backend /api/tuning/auth/verify
 * 3. If backend returns 200, proxy sets its own httpOnly cookie for the frontend domain
 * 4. Protected tuning endpoints check this cookie
 * 
 * Note: We set our own cookie because backend cookies are for the backend domain,
 * which won't work when frontend and backend are on different hosts.
 */

// Backend API URL - configured via environment variable
const BACKEND_API_URL = process.env.BACKEND_API_URL || 'http://localhost:8001';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { password } = req.body;

  if (!password) {
    return res.status(400).json({ error: 'Password required' });
  }

  try {
    const backendUrl = `${BACKEND_API_URL}/api/tuning/auth/verify`;
    console.log('[Tuning Auth] Attempting to reach backend:', backendUrl);
    
    // Call backend tuning auth endpoint with timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
    
    const response = await fetch(backendUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ password }),
      signal: controller.signal,
    });

    clearTimeout(timeoutId);
    console.log('[Tuning Auth] Backend response status:', response.status);

    if (response.ok) {
      // Backend validated the password - set our own cookie for the frontend domain
      // This is necessary because backend cookies won't work cross-origin
      // Path=/ ensures cookie is sent to all routes including /tuning/*
      const isProduction = process.env.NODE_ENV === 'production';
      
      res.setHeader('Set-Cookie', [
        `tuning_auth=authenticated; Path=/; HttpOnly; SameSite=Lax; Max-Age=86400${isProduction ? '; Secure' : ''}`
      ]);
      
      console.log('[Tuning Auth] Authentication successful, cookie set with Path=/');
      return res.status(200).json({ success: true, message: 'Authentication successful' });
    } else if (response.status === 401) {
      console.log('[Tuning Auth] Invalid password');
      return res.status(401).json({ error: 'Invalid password' });
    } else if (response.status === 503) {
      console.log('[Tuning Auth] Dashboard not configured');
      return res.status(503).json({ error: 'Tuning dashboard not configured' });
    } else {
      console.log('[Tuning Auth] Unexpected status:', response.status);
      const errorText = await response.text();
      console.log('[Tuning Auth] Error response:', errorText);
      return res.status(500).json({ error: 'Authentication failed' });
    }
  } catch (error: any) {
    console.error('[Tuning Auth] Connection error:', error.message);
    return res.status(500).json({ 
      error: 'Connection error',
      details: error.message,
      backend_url: BACKEND_API_URL
    });
  }
}
