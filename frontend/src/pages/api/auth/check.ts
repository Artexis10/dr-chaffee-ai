import { NextApiRequest, NextApiResponse } from 'next';
import { verifySessionToken } from '../../../utils/authToken';

/**
 * Auth Check endpoint - determines if user needs to enter password.
 * 
 * Returns requiresPassword: false if:
 * - APP_PASSWORD is not set (no password protection), OR
 * - User has a valid auth_token cookie (already logged in)
 * 
 * Returns requiresPassword: true if:
 * - APP_PASSWORD is set AND user has no valid auth_token cookie
 */
export default function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const appPassword = process.env.APP_PASSWORD;
  const passwordConfigured = !!appPassword && appPassword.trim().length > 0;
  
  console.log('[Auth Check] APP_PASSWORD configured:', passwordConfigured);
  
  // If no password is configured, no login required
  if (!passwordConfigured) {
    console.log('[Auth Check] No password configured, access granted');
    return res.status(200).json({ requiresPassword: false });
  }
  
  // Password is configured - check if user has a valid session token
  const authToken = req.cookies.auth_token;
  
  if (authToken) {
    const payload = verifySessionToken(authToken);
    if (payload) {
      console.log('[Auth Check] Valid auth_token found, access granted');
      return res.status(200).json({ requiresPassword: false });
    } else {
      console.log('[Auth Check] auth_token present but invalid/expired');
    }
  } else {
    console.log('[Auth Check] No auth_token cookie found');
  }
  
  // No valid session - require password
  console.log('[Auth Check] Requires password: true');
  return res.status(200).json({ requiresPassword: true });
}
