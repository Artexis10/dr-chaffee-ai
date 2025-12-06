import { NextApiRequest, NextApiResponse } from 'next';
import { BACKEND_API_URL } from '../../../../utils/env';

/**
 * Discord Login Proxy - Fetches Discord OAuth URL from backend and redirects
 * 
 * This proxy allows the frontend to initiate the Discord OAuth flow
 * by fetching the authorization URL from the backend and redirecting the user.
 * 
 * IMPORTANT: We fetch the redirect URL server-side rather than redirecting
 * directly to the backend URL. This prevents exposing the internal backend
 * URL to the browser and ensures the OAuth flow works correctly with HTTPS.
 */

export default async function handler(req: NextApiRequest, res: NextApiResponse): Promise<void> {
  if (req.method !== 'GET') {
    res.status(405).json({ error: 'Method not allowed' });
    return;
  }

  console.log('[Discord Auth] Initiating OAuth flow via backend:', BACKEND_API_URL);

  try {
    // Fetch the Discord authorization URL from the backend
    // The backend will return a redirect to Discord's OAuth page
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000);
    
    const response = await fetch(`${BACKEND_API_URL}/api/auth/discord/login`, {
      method: 'GET',
      redirect: 'manual', // Don't follow redirects - we want to get the Location header
      signal: controller.signal,
    });
    
    clearTimeout(timeoutId);
    
    // The backend returns a 302 redirect to Discord's OAuth page
    if (response.status === 302 || response.status === 307) {
      const discordAuthUrl = response.headers.get('location');
      
      if (!discordAuthUrl) {
        console.error('[Discord Auth] Backend returned redirect but no Location header');
        res.status(500).json({ error: 'Invalid redirect from backend' });
        return;
      }
      
      console.log('[Discord Auth] Redirecting to Discord OAuth URL');
      
      // Forward any cookies from the backend response (e.g., state cookie)
      const setCookieHeader = response.headers.get('set-cookie');
      if (setCookieHeader) {
        res.setHeader('Set-Cookie', setCookieHeader);
      }
      
      res.redirect(302, discordAuthUrl);
      return;
    }
    
    // Handle non-redirect responses (errors)
    if (!response.ok) {
      const errorText = await response.text().catch(() => 'Unknown error');
      console.error('[Discord Auth] Backend error:', response.status, errorText);
      res.status(response.status).json({ 
        error: 'Discord OAuth not available',
        details: errorText 
      });
      return;
    }
    
    // Unexpected response
    console.error('[Discord Auth] Unexpected response from backend:', response.status);
    res.status(500).json({ error: 'Unexpected response from backend' });
    
  } catch (error: any) {
    console.error('[Discord Auth] Failed to initiate OAuth:', error.message);
    
    if (error.name === 'AbortError') {
      res.status(504).json({ error: 'Backend timeout' });
      return;
    }
    
    res.status(503).json({ 
      error: 'Discord OAuth service unavailable',
      message: 'Could not connect to authentication service'
    });
  }
}
