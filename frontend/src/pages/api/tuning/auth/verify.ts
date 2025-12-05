import { NextApiRequest, NextApiResponse } from 'next';
import { createSessionToken } from '../../../../utils/authToken';

/**
 * Tuning Auth Verify - Proxy to backend tuning authentication
 * 
 * Flow:
 * 1. Frontend sends password to this proxy
 * 2. Proxy forwards to backend /api/tuning/auth/verify
 * 3. If backend returns 200, proxy sets BOTH:
 *    - tuning_auth httpOnly cookie (for tuning dashboard)
 *    - auth_token cookie (for main app - shared session)
 * 4. This enables single sign-on: logging into tuning also logs into main app
 * 
 * Note: We set our own cookies because backend cookies are for the backend domain,
 * which won't work when frontend and backend are on different hosts.
 */

// Backend API URL - configured via environment variable
// Use the same import as other tuning endpoints for consistency
import { BACKEND_API_URL } from '../../../../utils/env';

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
      // Backend validated the password - set cookies for BOTH tuning and main app
      // This enables single sign-on: logging into tuning also logs into main app
      const isProduction = process.env.NODE_ENV === 'production';
      
      // Generate signed session token for main app auth
      let mainAppToken: string;
      try {
        mainAppToken = createSessionToken();
      } catch (error) {
        console.error('[Tuning Auth] Failed to create session token:', error);
        mainAppToken = '';
      }
      
      // Build cookie array - tuning_auth for dashboard, auth_token for main app
      // IMPORTANT: tuning_auth must NOT be HttpOnly so it can be read by the catch-all proxy
      // Actually, Next.js API routes CAN read HttpOnly cookies from req.cookies
      // The issue might be something else - let's add more logging
      const cookies = [
        `tuning_auth=authenticated; Path=/; HttpOnly; SameSite=Lax; Max-Age=86400${isProduction ? '; Secure' : ''}`
      ];
      
      // Also set main app auth token if we successfully created one
      if (mainAppToken) {
        const maxAge = 7 * 24 * 60 * 60; // 7 days
        cookies.push(
          `auth_token=${encodeURIComponent(mainAppToken)}; Path=/; SameSite=Lax; Max-Age=${maxAge}${isProduction ? '; Secure' : ''}`
        );
      }
      
      res.setHeader('Set-Cookie', cookies);
      
      console.log('[Tuning Auth] Authentication successful, setting cookies:', cookies.map(c => c.split('=')[0]));
      return res.status(200).json({ 
        success: true, 
        message: 'Authentication successful',
        token: mainAppToken || undefined // Return token so frontend can also store in localStorage
      });
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
  } catch (error: unknown) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    console.error('[Tuning Auth] Connection error:', errorMessage);
    return res.status(500).json({ 
      error: 'Connection error',
      details: errorMessage,
      backend_url: BACKEND_API_URL
    });
  }
}
