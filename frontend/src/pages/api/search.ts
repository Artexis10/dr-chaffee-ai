import { NextApiRequest, NextApiResponse } from 'next';
import { BACKEND_API_URL, INTERNAL_API_KEY } from '../../utils/env';

/**
 * Search API proxy - forwards requests to backend with internal API key.
 * 
 * ARCHITECTURE:
 * - Frontend (Vercel) → This proxy → Backend (Coolify/Hetzner) /search endpoint
 * - Backend generates embeddings IN-PROCESS (no separate embedding service)
 * - The "Embedding service error" message refers to the backend /search endpoint failing
 * 
 * This prevents direct public access to the backend /search endpoint.
 * The INTERNAL_API_KEY is injected here and validated by the backend.
 */

interface SearchResult {
  id: number;
  title: string;
  text: string;
  url: string;
  start_time_seconds: number;
  end_time_seconds: number;
  similarity: string; // Now a percentage string like "56.7"
  source_type: string;
  published_at?: string;
  rerank_score?: number;
}

interface SearchParams {
  query: string;
  source_filter?: 'all' | 'youtube' | 'zoom';
  year_filter?: string;
  limit?: number;
}

interface ClusteredResult {
  id: number;
  title: string;
  url: string;
  source_type: string;
  published_at?: string;
  segments: SearchResult[];
}

// Cluster segments within ±120 seconds of each other
function clusterSegments(results: SearchResult[]): SearchResult[] {
  if (results.length === 0) return results;
  
  const grouped: { [key: string]: SearchResult[] } = {};
  
  // Group by source URL (without timestamp)
  results.forEach(result => {
    const baseUrl = result.url.split('&t=')[0];
    if (!grouped[baseUrl]) {
      grouped[baseUrl] = [];
    }
    grouped[baseUrl].push(result);
  });
  
  const clustered: SearchResult[] = [];
  
  Object.values(grouped).forEach(sourceResults => {
    sourceResults.sort((a, b) => a.start_time_seconds - b.start_time_seconds);
    
    let currentCluster: SearchResult[] = [];
    
    sourceResults.forEach(result => {
      if (currentCluster.length === 0) {
        currentCluster.push(result);
      } else {
        const lastResult = currentCluster[currentCluster.length - 1];
        const timeDiff = Math.abs(result.start_time_seconds - lastResult.end_time_seconds);
        
        if (timeDiff <= 120) { // Within 120 seconds
          currentCluster.push(result);
        } else {
          // Finalize current cluster
          if (currentCluster.length > 1) {
            // Create merged segment
            const firstSegment = currentCluster[0];
            const lastSegment = currentCluster[currentCluster.length - 1];
            
            clustered.push({
              ...firstSegment,
              text: currentCluster.map(s => s.text).join(' ... '),
              end_time_seconds: lastSegment.end_time_seconds,
              similarity: Math.max(...currentCluster.map(s => parseFloat(s.similarity))).toFixed(1)
            });
          } else {
            clustered.push(currentCluster[0]);
          }
          
          // Start new cluster
          currentCluster = [result];
        }
      }
    });
    
    // Handle final cluster
    if (currentCluster.length > 1) {
      const firstSegment = currentCluster[0];
      const lastSegment = currentCluster[currentCluster.length - 1];
      
      clustered.push({
        ...firstSegment,
        text: currentCluster.map(s => s.text).join(' ... '),
        end_time_seconds: lastSegment.end_time_seconds,
        similarity: Math.max(...currentCluster.map(s => parseFloat(s.similarity))).toFixed(1)
      });
    } else if (currentCluster.length === 1) {
      clustered.push(currentCluster[0]);
    }
  });
  
  return clustered;
}

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'POST' && req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  // Handle both GET and POST requests
  const params = req.method === 'POST' ? req.body : req.query;
  const query = params.q || params.query;
  const source_filter = params.source_filter || 'all';
  const year_filter = params.year_filter;
  const limit = parseInt(params.limit as string) || 100; // Increased from 30 to get more diverse results before clustering

  if (!query || typeof query !== 'string' || query.trim().length === 0) {
    return res.status(400).json({ error: 'Query is required' });
  }

  try {
    // Call backend API for semantic search
    console.log(`[Search API] Proxying to backend: ${BACKEND_API_URL}/search`);
    console.log(`[Search API] Query: "${query.substring(0, 50)}...", limit=${limit}`);
    
    // Build headers with internal API key for backend authentication
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (INTERNAL_API_KEY) {
      headers['X-Internal-Key'] = INTERNAL_API_KEY;
    }
    
    const embeddingResponse = await fetch(`${BACKEND_API_URL}/search`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        query: query,
        top_k: limit,
        min_similarity: 0.3,
        use_reranking: process.env.RERANK_ENABLED === 'true'
      }),
    });

    if (!embeddingResponse.ok) {
      // Get the actual error details from backend
      let errorDetail = '';
      try {
        const errorBody = await embeddingResponse.json();
        errorDetail = errorBody.detail || JSON.stringify(errorBody);
      } catch {
        errorDetail = await embeddingResponse.text().catch(() => 'Unknown error');
      }
      console.error(`[Search API] Backend error: ${embeddingResponse.status} - ${errorDetail}`);
      throw new Error(`Backend returned ${embeddingResponse.status}: ${errorDetail}`);
    }

    const embeddingData = await embeddingResponse.json();
    console.log('[Search API] Backend returned:', embeddingData.total_results, 'results');

    // Transform results to match expected format
    let searchResults = embeddingData.results.map((row: any) => {
      let urlWithTimestamp = row.url;
      if (row.source_type === 'youtube' && row.start_time_seconds) {
        const timestampSeconds = Math.floor(row.start_time_seconds);
        urlWithTimestamp = `${row.url}&t=${timestampSeconds}s`;
      }
      return {
        id: row.id,
        title: row.title,
        text: row.text,
        url: urlWithTimestamp,
        start_time_seconds: row.start_time_seconds,
        end_time_seconds: row.end_time_seconds,
        similarity: (row.similarity * 100).toFixed(1),
        source_type: row.source_type,
        published_at: row.published_at,
      };
    });

    // Apply filters if needed (embedding service doesn't support filters yet)
    if (source_filter !== 'all') {
      searchResults = searchResults.filter((r: any) => r.source_type === source_filter);
    }
    if (year_filter) {
      searchResults = searchResults.filter((r: any) => {
        if (!r.published_at) return false;
        const year = new Date(r.published_at).getFullYear();
        return year === parseInt(year_filter);
      });
    }

    // Cluster segments within ±120s
    const clusteredResults = clusterSegments(searchResults);

    res.status(200).json({ 
      results: clusteredResults, 
      total: clusteredResults.length, 
      query: query.trim(),
      filters: {
        source_filter,
        year_filter
      }
    });

  } catch (error) {
    console.error('Search error:', error);
    
    // Handle different types of errors
    if (error instanceof Error) {
      // Database connection errors
      if (error.message.includes('connect') || 
          error.message.includes('ECONNREFUSED') || 
          error.message.includes('database') ||
          error.message.includes('Connection') ||
          error.message.includes('pool')) {
        return res.status(503).json({
          error: 'Database service unavailable',
          message: 'The database service is currently unavailable. Please try again later.',
          code: 'SERVICE_UNAVAILABLE'
        });
      }
      
      // Generic error with message
      res.status(500).json({ 
        error: 'Search service error',
        message: `The search service encountered an error: ${error.message}`,
        code: 'SEARCH_ERROR'
      });
    } else {
      // Unknown error type
      res.status(500).json({ 
        error: 'Search service error',
        message: 'The search service encountered an unknown error.',
        code: 'UNKNOWN_ERROR'
      });
    }
  }
}

// TODO: Implement semantic search with embeddings
// This would replace the text search above with:
// SELECT 
//   s.title, s.url, seg.text, seg.start_sec, seg.end_sec,
//   (seg.embedding <=> $1::vector) as similarity
// FROM segments seg
// JOIN sources s ON seg.source_id = s.id
// WHERE seg.speaker_label = 'Chaffee'
// ORDER BY seg.embedding <=> $1::vector
// LIMIT 20
