import { NextApiRequest, NextApiResponse } from 'next';
import { BACKEND_API_URL } from '../../../utils/env';

/**
 * Set Active Embedding Model - Proxy to backend tuning endpoint
 * 
 * Requires tuning authentication (tuning_auth cookie).
 */

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  // Check for tuning_auth cookie
  const tuningAuth = req.cookies.tuning_auth;
  if (tuningAuth !== 'authenticated') {
    return res.status(401).json({ error: 'Tuning authentication required' });
  }

  const { model_key } = req.body;

  if (!model_key) {
    return res.status(400).json({ error: 'model_key required' });
  }

  try {
    // Call backend to set active query model, forwarding the auth cookie
    const response = await fetch(`${BACKEND_API_URL}/api/tuning/models/query?model_key=${encodeURIComponent(model_key)}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Cookie': `tuning_auth=${tuningAuth}`,
      },
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || `Backend returned ${response.status}`);
    }

    const result = await response.json();
    return res.status(200).json(result);
  } catch (error: any) {
    console.error('Error setting active model:', error);
    return res.status(500).json({ error: error.message || 'Failed to set active model' });
  }
}
