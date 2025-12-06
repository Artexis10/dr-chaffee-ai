import { NextApiRequest, NextApiResponse } from 'next';
import { BACKEND_API_URL } from '../../../utils/env';

/**
 * Feedback Stats API Proxy
 * 
 * Proxies GET /api/feedback/stats to the backend.
 * Requires tuning_auth cookie (admin only).
 */

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  // Only allow GET
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }
  
  // Require tuning auth
  const tuningAuth = req.cookies.tuning_auth;
  if (tuningAuth !== 'authenticated') {
    console.log('[Feedback Stats Proxy] Auth required. Cookie value:', tuningAuth);
    return res.status(401).json({ error: 'Tuning authentication required' });
  }
  
  const backendUrl = `${BACKEND_API_URL}/api/feedback/stats`;
  
  try {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      'Cookie': `tuning_auth=${tuningAuth}`,
    };
    
    // Forward query string
    const params = new URLSearchParams();
    Object.entries(req.query).forEach(([key, value]) => {
      if (value) {
        params.set(key, Array.isArray(value) ? value[0] : value);
      }
    });
    
    const url = params.toString() ? `${backendUrl}?${params.toString()}` : backendUrl;
    
    console.log(`[Feedback Stats Proxy] GET ${url}`);
    
    const response = await fetch(url, {
      method: 'GET',
      headers,
    });
    
    const contentType = response.headers.get('content-type');
    
    console.log(`[Feedback Stats Proxy] Backend response status: ${response.status}`);
    
    // Forward the response status and body
    if (contentType?.includes('application/json')) {
      const data = await response.json();
      if (response.status !== 200) {
        console.log(`[Feedback Stats Proxy] Backend error response:`, data);
      }
      return res.status(response.status).json(data);
    } else {
      const text = await response.text();
      return res.status(response.status).send(text);
    }
  } catch (error: any) {
    console.error(`[Feedback Stats Proxy] Error:`, error.message);
    return res.status(500).json({
      error: 'Proxy error',
      details: error.message,
      backend_url: backendUrl,
    });
  }
}
