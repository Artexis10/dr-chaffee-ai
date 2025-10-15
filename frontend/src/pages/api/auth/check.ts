import { NextApiRequest, NextApiResponse } from 'next';

export default function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const appPassword = process.env.APP_PASSWORD;
  console.log('[Auth Check] APP_PASSWORD exists:', !!appPassword, 'length:', appPassword?.length || 0);
  
  const requiresPassword = !!appPassword && appPassword.trim().length > 0;
  console.log('[Auth Check] Requires password:', requiresPassword);
  
  res.status(200).json({
    requiresPassword
  });
}
