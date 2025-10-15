import { NextApiRequest, NextApiResponse } from 'next';

export default function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const authHeader = req.headers.authorization;
  const token = authHeader?.replace('Bearer ', '');

  // Simple token validation (in production, verify against database/Redis)
  // For now, we just check if token exists and has correct format
  if (token && token.length === 64) {
    res.status(200).json({ valid: true });
  } else {
    res.status(401).json({ valid: false });
  }
}
