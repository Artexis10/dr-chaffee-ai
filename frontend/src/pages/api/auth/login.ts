import { NextApiRequest, NextApiResponse } from 'next';
import { createSessionToken } from '../../../utils/authToken';

/**
 * Login endpoint - validates APP_PASSWORD and issues signed session token.
 * 
 * Required env vars:
 * - APP_PASSWORD: The password users must enter to access the app
 * - APP_SESSION_SECRET: Secret for signing session tokens (required in production)
 */
export default function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { password } = req.body;
  const appPassword = process.env.APP_PASSWORD;

  console.log('[Auth Login] Password attempt received');
  console.log('[Auth Login] APP_PASSWORD configured:', !!appPassword);

  // If no password is set, deny access
  if (!appPassword || appPassword.trim().length === 0) {
    console.log('[Auth Login] No password configured, denying access');
    return res.status(403).json({ error: 'Password protection not configured' });
  }

  // Check password
  if (password === appPassword) {
    console.log('[Auth Login] Password correct, generating signed token');
    
    try {
      // Generate signed session token (HMAC-SHA256)
      const token = createSessionToken();
      
      // Set auth_token cookie (7 days expiry, matching token expiry)
      // httpOnly: false so PasswordGate can read it from localStorage as backup
      // secure: true in production (HTTPS only)
      // sameSite: lax for reasonable CSRF protection while allowing normal navigation
      const isProduction = process.env.NODE_ENV === 'production';
      
      // Build cookie string manually (no external dependency needed)
      const maxAge = 7 * 24 * 60 * 60;  // 7 days
      const cookieParts = [
        `auth_token=${encodeURIComponent(token)}`,
        `Max-Age=${maxAge}`,
        'Path=/',
        'SameSite=Lax',
      ];
      if (isProduction) {
        cookieParts.push('Secure');
      }
      res.setHeader('Set-Cookie', cookieParts.join('; '));
      
      res.status(200).json({ 
        success: true, 
        token,
        message: 'Authentication successful'
      });
    } catch (error) {
      console.error('[Auth Login] Token generation failed:', error);
      res.status(500).json({ error: 'Failed to generate session token' });
    }
  } else {
    console.log('[Auth Login] Password incorrect');
    res.status(401).json({ error: 'Invalid password' });
  }
}
