import { NextApiRequest, NextApiResponse } from 'next';

/**
 * Stats API - Thin proxy to backend /stats endpoint
 * 
 * Architecture: Frontend → Backend → Postgres
 * The frontend never connects directly to the database.
 */
export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const backendBaseUrl = process.env.BACKEND_API_URL;
  
  if (!backendBaseUrl) {
    console.error('Stats API error: BACKEND_API_URL not configured');
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
    const response = await fetch(`${backendBaseUrl}/stats`);
    
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
