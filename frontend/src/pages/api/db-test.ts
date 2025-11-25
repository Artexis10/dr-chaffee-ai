import { NextApiRequest, NextApiResponse } from 'next';

/**
 * Database test endpoint - Proxies to backend /health endpoint
 * 
 * Architecture: Frontend → Backend → Postgres
 * The frontend never connects directly to the database.
 */
export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  const backendBaseUrl = process.env.BACKEND_API_URL;
  
  if (!backendBaseUrl) {
    return res.status(503).json({ 
      success: false, 
      message: 'BACKEND_API_URL not configured',
      error: 'Backend URL not set'
    });
  }

  try {
    const response = await fetch(`${backendBaseUrl}/health`);
    const data = await response.json();
    
    if (response.ok && data.checks?.database === 'ok') {
      res.status(200).json({ 
        success: true, 
        message: 'Database connection successful (via backend)',
        data: { test: 1 },
        backend_status: data
      });
    } else {
      res.status(503).json({ 
        success: false, 
        message: 'Database connection failed (via backend)',
        backend_status: data
      });
    }
  } catch (error) {
    console.error('Backend health check error:', error);
    
    res.status(500).json({ 
      success: false, 
      message: 'Backend connection failed',
      error: error instanceof Error ? error.message : 'Unknown error'
    });
  }
}
