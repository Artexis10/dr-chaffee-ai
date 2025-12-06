import { NextApiRequest, NextApiResponse } from 'next';

/**
 * Main App Logout - Clears auth_token and discord_user_id cookies
 * 
 * This endpoint clears the main app authentication cookies.
 * It does NOT clear tuning_auth - that's handled by /api/tuning/auth/logout.
 * 
 * Cookie clearing uses matching attributes from login:
 * - Path: /
 * - SameSite: Lax
 * - Max-Age: 0 (expires immediately)
 */
export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const isProduction = process.env.NODE_ENV === 'production';
  
  // Build cookie clearing strings with matching attributes from login
  // auth_token: set by /api/auth/login and Discord OAuth callback
  // discord_user_id: set by Discord OAuth callback
  const cookiesToClear = [
    // Clear auth_token (main app session)
    `auth_token=; Path=/; SameSite=Lax; Max-Age=0${isProduction ? '; Secure' : ''}`,
    // Clear discord_user_id (Discord user reference)
    `discord_user_id=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0${isProduction ? '; Secure' : ''}`,
  ];
  
  res.setHeader('Set-Cookie', cookiesToClear);
  
  console.log('[Auth Logout] Main app logout successful, cookies cleared: auth_token, discord_user_id');
  return res.status(200).json({ success: true, message: 'Logged out' });
}
