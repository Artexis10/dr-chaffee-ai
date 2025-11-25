import { NextApiRequest, NextApiResponse } from 'next';

// Backend API URL - configured via environment variable
const BACKEND_API_URL = process.env.BACKEND_API_URL || 'http://localhost:8001';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    // Get tuning config from backend
    const response = await fetch(`${BACKEND_API_URL}/api/tuning/models`, {
      headers: {
        'Content-Type': 'application/json',
      },
      credentials: 'include',
    });

    if (!response.ok) {
      throw new Error(`Backend returned ${response.status}`);
    }

    const models = await response.json();
    
    // Transform backend config to frontend format
    const transformedModels = models.map((model: any) => ({
      key: model.key,
      provider: model.provider || 'unknown',
      dimensions: model.dimensions || 0,
      cost_per_1k: model.cost_per_1k || 0,
      description: model.description || '',
      is_active_query: model.key === models.find((m: any) => m.is_active)?.key,
    }));

    return res.status(200).json(transformedModels);
  } catch (error) {
    console.error('Error fetching embedding models:', error);
    return res.status(500).json({ error: 'Failed to fetch embedding models' });
  }
}
