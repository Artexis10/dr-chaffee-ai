import { NextApiRequest, NextApiResponse } from 'next';
import { BACKEND_API_URL } from '../../../utils/env';

/**
 * Feedback API Proxy
 * 
 * Proxies feedback requests to the backend:
 * - POST: Create feedback (public, no auth required)
 * - GET: List feedback (requires tuning_auth for admin view)
 */

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  const backendUrl = `${BACKEND_API_URL}/api/feedback`;
  
  // GET requires tuning auth (admin only)
  if (req.method === 'GET') {
    const tuningAuth = req.cookies.tuning_auth;
    if (tuningAuth !== 'authenticated') {
      console.log('[Feedback Proxy] GET requires auth. Cookie value:', tuningAuth);
      return res.status(401).json({ error: 'Tuning authentication required' });
    }
  }
  
  try {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    
    // Forward tuning_auth cookie if present
    const tuningAuth = req.cookies.tuning_auth;
    if (tuningAuth) {
      headers['Cookie'] = `tuning_auth=${tuningAuth}`;
    }
    
    // Forward session ID if present
    const sessionId = req.headers['x-session-id'];
    if (sessionId) {
      headers['X-Session-ID'] = Array.isArray(sessionId) ? sessionId[0] : sessionId;
    }
    
    const fetchOptions: RequestInit = {
      method: req.method,
      headers,
    };
    
    // Include body for POST requests
    if (req.method === 'POST') {
      fetchOptions.body = JSON.stringify(req.body);
    }
    
    // Forward query string for GET requests
    let url = backendUrl;
    if (req.method === 'GET' && Object.keys(req.query).length > 0) {
      const params = new URLSearchParams();
      Object.entries(req.query).forEach(([key, value]) => {
        if (value) {
          params.set(key, Array.isArray(value) ? value[0] : value);
        }
      });
      url = `${backendUrl}?${params.toString()}`;
    }
    
    console.log(`[Feedback Proxy] ${req.method} ${url}`);
    
    const response = await fetch(url, fetchOptions);
    const contentType = response.headers.get('content-type');
    
    console.log(`[Feedback Proxy] Backend response status: ${response.status}`);
    
    // Forward the response status and body
    if (contentType?.includes('application/json')) {
      const data = await response.json();
      if (response.status !== 200 && response.status !== 201) {
        console.log(`[Feedback Proxy] Backend error response:`, data);
      }
      return res.status(response.status).json(data);
    } else {
      const text = await response.text();
      return res.status(response.status).send(text);
    }
  } catch (error: any) {
    console.error(`[Feedback Proxy] Error:`, error.message);
    return res.status(500).json({
      error: 'Proxy error',
      details: error.message,
      backend_url: backendUrl,
    });
  }
}
