import { NextApiRequest, NextApiResponse } from 'next';
import { Pool } from 'pg';

// Database connection
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: process.env.DATABASE_URL?.includes('render.com') || process.env.NODE_ENV === 'production' 
    ? { rejectUnauthorized: false } 
    : false
});

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    // Single optimized query to get all stats
    const result = await pool.query(`
      SELECT 
        (SELECT COUNT(*) FROM segments) as total_segments,
        (SELECT COUNT(DISTINCT source_id) FROM segments) as total_videos
    `);
    
    const stats = result.rows[0];
    const segmentCount = parseInt(stats.total_segments || '0');
    const videoCount = parseInt(stats.total_videos || '0');
    
    // Cache for 5 minutes (stats don't change often)
    res.setHeader('Cache-Control', 'public, s-maxage=300, stale-while-revalidate=600');
    
    res.status(200).json({
      segments: segmentCount,
      videos: videoCount,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    console.error('Stats API error:', error);
    // Return fallback values on error
    res.status(200).json({
      segments: 15000,
      videos: 300,
      timestamp: new Date().toISOString(),
      fallback: true
    });
  }
}
