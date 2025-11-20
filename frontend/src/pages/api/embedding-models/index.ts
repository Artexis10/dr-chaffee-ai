import { NextApiRequest, NextApiResponse } from 'next';

// Use Render production URL as default, fallback to localhost for development
const BACKEND_API_URL = process.env.BACKEND_API_URL || 
  (process.env.NODE_ENV === 'production' 
    ? 'https://drchaffee-backend.onrender.com' 
    : 'http://localhost:8001');

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    // Get tuning config from backend
    const response = await fetch(`${BACKEND_API_URL}/tuning/config`, {
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Backend returned ${response.status}`);
    }

    const config = await response.json();
    
    // Transform backend config to frontend format
    const models = Object.entries(config.models || {}).map(([key, model]: [string, any]) => ({
      key,
      provider: model.provider || 'unknown',
      dimensions: model.dimensions || 0,
      cost_per_1k: model.cost_per_1k || 0,
      description: model.description || '',
      is_active_query: key === config.active_query_model,
    }));

    return res.status(200).json(models);
  } catch (error) {
    console.error('Error fetching embedding models:', error);
    return res.status(500).json({ error: 'Failed to fetch embedding models' });
  }
}
