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
    // Call backend tuning auth endpoint (backend sets its own cookie)
    const response = await fetch(`${BACKEND_API_URL}/api/tuning/auth/verify`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ password }),
      credentials: 'include', // Important: allows cookies to be set
    });

    if (response.ok) {
      const data = await response.json();
      
      // Backend already set the httpOnly cookie, just forward the success
      // Extract the cookie from backend response and forward it
      const backendCookie = response.headers.get('set-cookie');
      if (backendCookie) {
        res.setHeader('Set-Cookie', backendCookie);
      }
      
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
