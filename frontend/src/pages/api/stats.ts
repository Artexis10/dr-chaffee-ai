import { NextApiRequest, NextApiResponse } from 'next';
import { BACKEND_API_URL, INTERNAL_API_KEY } from '../../utils/env';

/**
 * Stats API - Thin proxy to backend /stats endpoint
 * 
 * Architecture: Frontend → Backend → Postgres
 * The frontend never connects directly to the database.
 * 
 * Auth: Requires INTERNAL_API_KEY to be set and passed via X-Internal-Key header.
 */

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  console.log(`[Stats API] Proxying to backend: ${BACKEND_API_URL}/stats`);
  
  if (!BACKEND_API_URL) {
    console.error('[Stats API] BACKEND_API_URL not configured');
    return res.status(200).json({
      total_segments: 0,
      total_videos: 0,
      segments_with_embeddings: 0,
      segments_missing_embeddings: 0,
      embedding_coverage: '0.0%',
      embedding_dimensions: 384,
      timestamp: new Date().toISOString(),
      error: 'BACKEND_API_URL not configured'
    });
  }

  try {
    // Build headers with internal API key for backend authentication
    const headers: Record<string, string> = {};
    if (INTERNAL_API_KEY) {
      headers['X-Internal-Key'] = INTERNAL_API_KEY;
    }
    
    const response = await fetch(`${BACKEND_API_URL}/stats`, { headers });
    
    if (!response.ok) {
      throw new Error(`Backend /stats responded with ${response.status}`);
    }
    
    const data = await response.json();
    
    // Cache for 5 minutes (stats don't change often)
    res.setHeader('Cache-Control', 'public, s-maxage=300, stale-while-revalidate=600');
    
    return res.status(200).json(data);
  } catch (error) {
    console.error('Stats API error (frontend proxy):', error);
    // Return safe defaults on error
    return res.status(200).json({
      total_segments: 0,
      total_videos: 0,
      segments_with_embeddings: 0,
      segments_missing_embeddings: 0,
      embedding_coverage: '0.0%',
      embedding_dimensions: 384,
      timestamp: new Date().toISOString(),
      fallback: true
    });
  }
}
