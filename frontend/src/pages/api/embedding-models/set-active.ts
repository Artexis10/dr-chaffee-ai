import { NextApiRequest, NextApiResponse } from 'next';

// Backend API URL - configured via environment variable
const BACKEND_API_URL = process.env.BACKEND_API_URL || 'http://localhost:8001';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { model_key } = req.body;

  if (!model_key) {
    return res.status(400).json({ error: 'model_key required' });
  }

  try {
    // Call backend to set active query model
    const response = await fetch(`${BACKEND_API_URL}/tuning/set-query-model`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ model_key }),
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
