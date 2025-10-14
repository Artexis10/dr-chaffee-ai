import { NextApiRequest, NextApiResponse } from 'next';
import { Pool } from 'pg';

// Database connection
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: false
});

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    // Get segment count
    const segmentResult = await pool.query(
      "SELECT COUNT(*) as count FROM segments WHERE speaker_label = 'Chaffee'"
    );
    
    // Get video count
    const videoResult = await pool.query(
      "SELECT COUNT(DISTINCT source_id) as count FROM sources WHERE source_type = 'youtube'"
    );
    
    const segmentCount = parseInt(segmentResult.rows[0]?.count || '0');
    const videoCount = parseInt(videoResult.rows[0]?.count || '0');
    
    res.status(200).json({
      segments: segmentCount,
      videos: videoCount,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    console.error('Stats API error:', error);
    // Return fallback values on error
    res.status(200).json({
      segments: 1695,
      videos: 26,
      timestamp: new Date().toISOString(),
      fallback: true
    });
  }
}
