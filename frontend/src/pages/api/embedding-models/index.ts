import { NextApiRequest, NextApiResponse } from 'next';
import { BACKEND_API_URL } from '../../../utils/env';

/**
 * Embedding Models API - Proxy to backend tuning/models endpoint
 * 
 * Requires tuning authentication (tuning_auth cookie).
 */

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  // Check for tuning_auth cookie
  const tuningAuth = req.cookies.tuning_auth;
  if (tuningAuth !== 'authenticated') {
    return res.status(401).json({ error: 'Tuning authentication required' });
  }

  try {
    // Get tuning config from backend, forwarding the auth cookie
    const response = await fetch(`${BACKEND_API_URL}/api/tuning/models`, {
      headers: {
        'Content-Type': 'application/json',
        'Cookie': `tuning_auth=${tuningAuth}`,
      },
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
