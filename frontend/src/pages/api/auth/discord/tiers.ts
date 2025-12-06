import { NextApiRequest, NextApiResponse } from 'next';
import { BACKEND_API_URL } from '../../../../utils/env';

/**
 * Discord Tiers Proxy - Fetches available membership tiers from backend
 * 
 * Proxies the request to backend /auth/discord/tiers endpoint.
 */

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);
    
    const response = await fetch(`${BACKEND_API_URL}/api/auth/discord/tiers`, {
      signal: controller.signal,
    });
    
    clearTimeout(timeoutId);
    
    if (response.ok) {
      const data = await response.json();
      return res.status(200).json(data);
    } else {
      console.error('[Discord Tiers] Backend error:', response.status);
      return res.status(response.status).json({ error: 'Backend error' });
    }
  } catch (error) {
    console.error('[Discord Tiers] Error fetching tiers:', error);
    return res.status(500).json({ error: 'Failed to fetch tiers' });
  }
}
