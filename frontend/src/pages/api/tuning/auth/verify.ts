import { NextApiRequest, NextApiResponse } from 'next';

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
      credentials: 'include',
      signal: controller.signal,
    });

    clearTimeout(timeoutId);
    console.log('[Tuning Auth] Backend response status:', response.status);

    if (response.ok) {
      const data = await response.json();
      
      // Backend already set the httpOnly cookie, just forward the success
      const backendCookie = response.headers.get('set-cookie');
      if (backendCookie) {
        res.setHeader('Set-Cookie', backendCookie);
      }
      
      console.log('[Tuning Auth] Authentication successful');
      return res.status(200).json({ success: true });
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
