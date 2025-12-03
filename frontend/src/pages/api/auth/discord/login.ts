import { NextApiRequest, NextApiResponse } from 'next';

/**
 * Discord Login Proxy - Redirects to backend Discord OAuth login endpoint
 * 
 * This proxy allows the frontend to initiate the Discord OAuth flow
 * by redirecting to the backend's /auth/discord/login endpoint.
 */

const BACKEND_API_URL = process.env.BACKEND_API_URL || 'http://localhost:8000';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  // Redirect to backend Discord login endpoint
  const backendLoginUrl = `${BACKEND_API_URL}/auth/discord/login`;
  
  console.log('[Discord Auth] Redirecting to backend:', backendLoginUrl);
  
  res.redirect(302, backendLoginUrl);
}
