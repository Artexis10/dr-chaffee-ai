import { NextApiRequest, NextApiResponse } from 'next';

/**
 * Tuning Auth Logout - Clears the tuning_auth httpOnly cookie
 */
export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  // Clear the httpOnly cookie by setting it with max-age=0
  res.setHeader('Set-Cookie', [
    `tuning_auth=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0`
  ]);
  
  console.log('[Tuning Auth] Logout successful, cookie cleared');
  return res.status(200).json({ success: true, message: 'Logged out' });
}
