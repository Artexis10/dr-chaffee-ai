import { NextApiRequest, NextApiResponse } from 'next';
import { BACKEND_API_URL } from '../../../utils/env';

/**
 * Admin API Catch-All Proxy
 * 
 * Forwards all /api/admin/* requests to the backend, including the tuning_auth cookie.
 * This is used for admin endpoints like daily-summaries that require tuning auth.
 * 
 * Protected endpoints on the backend require the tuning_auth cookie.
 * This proxy forwards the cookie from the frontend domain to the backend.
 */

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  // Get the path segments after /api/admin/
  const { path } = req.query;
  const pathSegments = Array.isArray(path) ? path : [path];
  const subPath = pathSegments.join('/');
  
  // Check for tuning_auth cookie (set by our auth/verify endpoint)
  const tuningAuth = req.cookies.tuning_auth;
  if (tuningAuth !== 'authenticated') {
    console.log(`[Admin Proxy] Auth check failed for ${subPath}. Cookie value:`, tuningAuth);
    return res.status(401).json({ error: 'Tuning authentication required' });
  }
  
  const backendUrl = `${BACKEND_API_URL}/api/admin/${subPath}`;
  console.log(`[Admin Proxy] ${req.method} ${backendUrl}`);
  
  try {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      // Forward the tuning_auth cookie to backend
      'Cookie': `tuning_auth=${tuningAuth}`,
    };
    
    const fetchOptions: RequestInit = {
      method: req.method,
      headers,
    };
    
    // Include body for POST/PUT/PATCH requests
    if (['POST', 'PUT', 'PATCH'].includes(req.method || '')) {
      fetchOptions.body = JSON.stringify(req.body);
    }
    
    // Forward query string
    const url = new URL(backendUrl);
    Object.entries(req.query).forEach(([key, value]) => {
      if (key !== 'path' && value) {
        url.searchParams.set(key, Array.isArray(value) ? value[0] : value);
      }
    });
    
    const response = await fetch(url.toString(), fetchOptions);
    const contentType = response.headers.get('content-type');
    
    console.log(`[Admin Proxy] Backend response status: ${response.status}`);
    
    // Forward the response status and body
    if (contentType?.includes('application/json')) {
      const data = await response.json();
      if (response.status !== 200) {
        console.log(`[Admin Proxy] Backend error response:`, data);
      }
      return res.status(response.status).json(data);
    } else {
      const text = await response.text();
      return res.status(response.status).send(text);
    }
  } catch (error: any) {
    console.error(`[Admin Proxy] Error:`, error.message);
    return res.status(500).json({
      error: 'Proxy error',
      details: error.message,
      backend_url: backendUrl,
    });
  }
}
