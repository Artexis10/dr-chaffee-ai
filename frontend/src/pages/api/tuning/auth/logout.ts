import { NextApiRequest, NextApiResponse } from 'next';

/**
 * Tuning Auth Logout - Clears BOTH tuning_auth and auth_token cookies
 * This ensures logging out from tuning also logs out from the main app (shared session)
 */
export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  // Clear both cookies by setting them with max-age=0
  // This ensures logout from tuning also logs out from main app
  res.setHeader('Set-Cookie', [
    `tuning_auth=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0`,
    `auth_token=; Path=/; SameSite=Lax; Max-Age=0`
  ]);
  
  console.log('[Tuning Auth] Logout successful, both cookies cleared');
  return res.status(200).json({ success: true, message: 'Logged out' });
}
