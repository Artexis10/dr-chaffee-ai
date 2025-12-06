import { NextApiRequest, NextApiResponse } from 'next';

/**
 * Tuning Auth Logout - Clears tuning_auth cookie ONLY
 * 
 * This endpoint clears the tuning dashboard authentication cookie.
 * It does NOT clear auth_token - main app and tuning have separate sessions.
 * 
 * After tuning logout:
 * - User is redirected to / (main app)
 * - If they have a valid auth_token, they can still use the main app
 * - If they try to access /tuning, they'll need to re-authenticate
 */
export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const isProduction = process.env.NODE_ENV === 'production';
  
  // Clear only tuning_auth cookie - do NOT clear auth_token
  // Main app and tuning dashboard have separate sessions
  res.setHeader('Set-Cookie', [
    `tuning_auth=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0${isProduction ? '; Secure' : ''}`,
  ]);
  
  console.log('[Tuning Auth] Logout successful, tuning_auth cookie cleared');
  return res.status(200).json({ success: true, message: 'Logged out from tuning' });
}
