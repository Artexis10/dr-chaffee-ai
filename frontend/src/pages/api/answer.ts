import { NextApiRequest, NextApiResponse } from 'next';

/**
 * Answer API - Thin proxy to backend /answer endpoint
 * 
 * Architecture: Frontend → Backend → OpenAI
 * The frontend NEVER calls OpenAI directly. All answer generation happens on the backend.
 * 
 * Auth: Requires INTERNAL_API_KEY to be set and passed via X-Internal-Key header.
 */

// Backend API URL - configured via environment variable
const BACKEND_API_URL = process.env.BACKEND_API_URL || 'http://localhost:8001';

// Internal API key for backend authentication
const INTERNAL_API_KEY = process.env.INTERNAL_API_KEY;

// Configure API route for longer timeouts (needed for answer generation)
export const config = {
  api: {
    responseLimit: false,
    bodyParser: {
      sizeLimit: '1mb',
    },
  },
};

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  // Support both GET and POST
  if (req.method !== 'GET' && req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  // Extract query parameters
  let query: string;
  let top_k: number = 50;
  let style: string = 'concise';

  if (req.method === 'GET') {
    query = req.query.q as string || req.query.query as string;
    if (req.query.top_k) top_k = parseInt(req.query.top_k as string, 10);
    if (req.query.style) style = req.query.style as string;
  } else {
    query = req.body.query || req.body.q;
    if (req.body.top_k) top_k = req.body.top_k;
    if (req.body.style) style = req.body.style;
  }

  if (!query) {
    return res.status(400).json({ error: 'Query parameter "q" or "query" is required' });
  }

  if (!BACKEND_API_URL) {
    console.error('[Answer API] BACKEND_API_URL not configured');
    return res.status(503).json({
      error: 'Backend not configured',
      message: 'BACKEND_API_URL environment variable is not set.',
      code: 'BACKEND_NOT_CONFIGURED'
    });
  }

  try {
    console.log(`[Answer API] Proxying to backend: query="${query}", top_k=${top_k}, style=${style}`);

    // Build headers with internal API key
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (INTERNAL_API_KEY) {
      headers['X-Internal-Key'] = INTERNAL_API_KEY;
    }

    // Forward request to backend
    const backendUrl = `${BACKEND_API_URL}/answer`;
    const response = await fetch(backendUrl, {
      method: 'POST',
      headers,
      body: JSON.stringify({ query, top_k, style }),
      signal: AbortSignal.timeout(120000), // 2 minute timeout for answer generation
    });

    // Get response body
    const contentType = response.headers.get('content-type');
    let data: any;
    
    if (contentType?.includes('application/json')) {
      data = await response.json();
    } else {
      const text = await response.text();
      data = { error: 'Unexpected response format', details: text };
    }

    // Forward backend response status and body
    if (!response.ok) {
      console.error(`[Answer API] Backend error: ${response.status}`, data);
      
      // Map backend errors to user-friendly messages
      if (response.status === 401) {
        return res.status(401).json({
          error: 'Authentication failed',
          message: 'Internal API key mismatch.',
          code: 'AUTH_FAILED'
        });
      }
      if (response.status === 503) {
        return res.status(503).json({
          error: 'Service unavailable',
          message: data.detail || 'Answer generation service is not available.',
          code: 'SERVICE_UNAVAILABLE'
        });
      }
      if (response.status === 404) {
        return res.status(200).json({
          error: 'No relevant content',
          message: data.detail || 'No relevant information found for this query.',
          code: 'NO_CONTENT'
        });
      }
      
      return res.status(response.status).json({
        error: 'Answer generation failed',
        message: data.detail || 'An error occurred while generating the answer.',
        code: 'GENERATION_FAILED'
      });
    }

    console.log(`[Answer API] Success: ${data.chunks_used || 0} chunks used`);
    
    // Return backend response directly
    return res.status(200).json(data);

  } catch (error: any) {
    console.error('[Answer API] Proxy error:', error.message);

    // Handle timeout
    if (error.name === 'TimeoutError' || error.message?.includes('timeout')) {
      return res.status(504).json({
        error: 'Request timeout',
        message: 'Answer generation took too long. Please try a simpler question.',
        code: 'TIMEOUT'
      });
    }

    // Handle connection errors
    if (error.message?.includes('ECONNREFUSED') || error.message?.includes('fetch failed')) {
      return res.status(503).json({
        error: 'Backend unavailable',
        message: 'Cannot connect to the answer service. Please try again later.',
        code: 'BACKEND_UNAVAILABLE'
      });
    }

    return res.status(500).json({
      error: 'Proxy error',
      message: error.message || 'An unexpected error occurred.',
      code: 'PROXY_ERROR'
    });
  }
}
