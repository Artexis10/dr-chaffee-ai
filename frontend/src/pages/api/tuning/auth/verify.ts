import { NextApiRequest, NextApiResponse } from 'next';

const BACKEND_API_URL = process.env.BACKEND_API_URL || 'http://localhost:8001';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { password } = req.body;

  if (!password) {
    return res.status(400).json({ error: 'Password required' });
  }

  try {
    // Call backend tuning auth endpoint
    const response = await fetch(`${BACKEND_API_URL}/tuning/auth`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ password }),
    });

    if (response.ok) {
      const data = await response.json();
      
      // Set secure httpOnly cookie with the token
      res.setHeader('Set-Cookie', `tuning_token=${data.token}; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=86400`);
      
      return res.status(200).json({ success: true });
    } else if (response.status === 401) {
      return res.status(401).json({ error: 'Invalid password' });
    } else if (response.status === 503) {
      return res.status(503).json({ error: 'Tuning dashboard not configured' });
    } else {
      return res.status(500).json({ error: 'Authentication failed' });
    }
  } catch (error) {
    console.error('Tuning auth error:', error);
    return res.status(500).json({ error: 'Connection error' });
  }
}
