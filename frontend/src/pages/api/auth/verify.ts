import { NextApiRequest, NextApiResponse } from 'next';
import { verifySessionToken } from '../../../utils/authToken';

/**
 * Verify endpoint - validates signed session token.
 * 
 * Checks:
 * 1. Token signature is valid (HMAC-SHA256)
 * 2. Token is not expired
 * 
 * Required env vars:
 * - APP_SESSION_SECRET: Secret for verifying session tokens (required in production)
 */
export default function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const authHeader = req.headers.authorization;
  const token = authHeader?.replace('Bearer ', '');

  if (!token) {
    return res.status(401).json({ valid: false, error: 'No token provided' });
  }

  // Verify signed token (checks signature and expiration)
  const payload = verifySessionToken(token);
  
  if (payload) {
    res.status(200).json({ valid: true });
  } else {
    res.status(401).json({ valid: false, error: 'Invalid or expired token' });
  }
}
