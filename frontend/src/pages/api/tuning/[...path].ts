import { NextApiRequest, NextApiResponse } from 'next';
import { BACKEND_API_URL } from '../../../utils/env';

/**
 * Tuning API Catch-All Proxy
 * 
 * Forwards all /api/tuning/* requests (except auth/verify which has its own handler)
 * to the backend, including the tuning_auth cookie for authentication.
 * 
 * Protected endpoints on the backend require the tuning_auth cookie.
 * This proxy forwards the cookie from the frontend domain to the backend.
 */

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  // Get the path segments after /api/tuning/
  const { path } = req.query;
  const pathSegments = Array.isArray(path) ? path : [path];
  const subPath = pathSegments.join('/');
  
  // Skip auth endpoints - they have their own handlers in /api/tuning/auth/
  // Next.js should route to specific files first, but we double-check here
  const authEndpoints = ['auth/verify', 'auth/status', 'auth/logout'];
  if (authEndpoints.includes(subPath)) {
    // Let the specific handler deal with it (this shouldn't normally be reached)
    return res.status(404).json({ error: `Use /api/tuning/${subPath} directly` });
  }
  
  // Check for tuning_auth cookie (set by our auth/verify endpoint)
  const tuningAuth = req.cookies.tuning_auth;
  if (tuningAuth !== 'authenticated') {
    console.log(`[Tuning Proxy] Auth check failed for ${subPath}. Cookie value:`, tuningAuth);
    return res.status(401).json({ error: 'Tuning authentication required' });
  }
  
  const backendUrl = `${BACKEND_API_URL}/api/tuning/${subPath}`;
  console.log(`[Tuning Proxy] ${req.method} ${backendUrl}`);
  console.log(`[Tuning Proxy] Forwarding cookie: tuning_auth=${tuningAuth}`);
  
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
    
    const response = await fetch(backendUrl, fetchOptions);
    const contentType = response.headers.get('content-type');
    
    console.log(`[Tuning Proxy] Backend response status: ${response.status}`);
    
    // Forward the response status and body
    if (contentType?.includes('application/json')) {
      const data = await response.json();
      if (response.status !== 200) {
        console.log(`[Tuning Proxy] Backend error response:`, data);
      }
      return res.status(response.status).json(data);
    } else {
      const text = await response.text();
      return res.status(response.status).send(text);
    }
  } catch (error: any) {
    console.error(`[Tuning Proxy] Error:`, error.message);
    return res.status(500).json({
      error: 'Proxy error',
      details: error.message,
      backend_url: backendUrl,
    });
  }
}
