import { NextApiRequest, NextApiResponse } from 'next';
import * as crypto from 'crypto';

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
    console.log('[Auth Login] Password correct, generating token');
    // Generate a simple token (in production, use JWT)
    const token = crypto.randomBytes(32).toString('hex');
    
    // Store token with expiry (you could use Redis or database in production)
    // For now, we'll just return it and verify on client side
    
    res.status(200).json({ 
      success: true, 
      token,
      message: 'Authentication successful'
    });
  } else {
    console.log('[Auth Login] Password incorrect');
    res.status(401).json({ error: 'Invalid password' });
  }
}
