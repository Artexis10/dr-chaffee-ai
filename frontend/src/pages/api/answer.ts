import { NextApiRequest, NextApiResponse } from 'next';
import { Pool } from 'pg';
import * as crypto from 'crypto';

// Import our RAG functionality
type RAGResponse = {
  question: string;
  answer: string;
  citations: Array<{
    video_id: string;
    title: string;
    timestamp: string;
    similarity: number;
  }>;
  chunks_used: number;
  cost_usd: number;
  timestamp: number;
};

// Database connection
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false
});

// Configuration
const ANSWER_ENABLED = process.env.ANSWER_ENABLED !== 'false'; // Default to enabled
const ANSWER_TOPK = parseInt(process.env.ANSWER_TOPK || '50'); // Increased from 40 for better quality
const ANSWER_TTL_HOURS = parseInt(process.env.ANSWER_TTL_HOURS || '336'); // 14 days
const SUMMARIZER_MODEL = process.env.SUMMARIZER_MODEL || 'gpt-4o'; // Upgraded from gpt-3.5-turbo for better quality
const ANSWER_STYLE_DEFAULT = process.env.ANSWER_STYLE_DEFAULT || 'concise';
const OPENAI_API_KEY = process.env.OPENAI_API_KEY;
const USE_MOCK_MODE = !OPENAI_API_KEY || OPENAI_API_KEY.includes('your_') || process.env.USE_MOCK_MODE === 'true';

console.log('ANSWER_ENABLED:', ANSWER_ENABLED);
console.log('USE_MOCK_MODE:', USE_MOCK_MODE);

// Backend API Integration
const BACKEND_API_URL = process.env.BACKEND_API_URL || process.env.EMBEDDING_SERVICE_URL || 'https://drchaffee-backend.onrender.com';

// Cache configuration
const CACHE_SIMILARITY_THRESHOLD = 0.92; // 92% similarity to consider a cache hit
const CACHE_TTL_HOURS = parseInt(process.env.ANSWER_CACHE_TTL_HOURS || '336'); // 14 days

async function callRAGService(question: string): Promise<RAGResponse | null> {
  try {
    // Create timeout promise
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout
    
    // Call the backend's /answer endpoint for RAG
    const response = await fetch(`${BACKEND_API_URL}/answer`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ query: question, top_k: 50 }),  // Use 50 for better quality
      signal: controller.signal
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      // Silently fail if RAG service doesn't have /search endpoint yet
      if (response.status !== 404) {
        console.error('RAG service error:', response.status, response.statusText);
      }
      return null;
    }

    const data = await response.json();
    
    // Transform RAG response to match our format
    return {
      question: data.question || question,
      answer: data.answer || '',
      citations: data.sources?.map((source: any) => ({
        video_id: source.video_id,
        title: source.title,
        timestamp: source.timestamp || '',
        similarity: source.similarity || 0
      })) || [],
      chunks_used: data.sources?.length || 0,
      cost_usd: data.cost_usd || 0,
      timestamp: Date.now()
    };
  } catch (error) {
    console.error('RAG service call failed:', error);
    return null;
  }
}

interface AnswerParams {
  q: string;
  max_context?: number;
  max_bullets?: number;
  style?: 'concise' | 'detailed';
  refresh?: boolean;
}

interface ChunkResult {
  id: number;
  source_id: number;
  video_id: string;
  title: string;
  text: string;
  start_time_seconds: number;
  end_time_seconds: number;
  published_at: string;
  source_type: string;
  similarity: number;
}

interface Citation {
  video_id: string;
  title: string;
  t_start_s: number;
  published_at: string;
}

interface AnswerResponse {
  answer_md: string;
  citations: Citation[];
  confidence: number;
  notes?: string;
  used_chunk_ids: string[];
}

interface LLMResponse {
  answer: string;
  citations: Array<{
    video_id: string;
    timestamp: string;
    date: string;
  }>;
  confidence: number;
  notes?: string;
}

// Utility functions
function normalizeQuery(query: string): string {
  return query.toLowerCase().trim().replace(/\s+/g, ' ');
}

function generateCacheKey(queryNorm: string, chunkIds: string[], modelVersion: string): string {
  const content = queryNorm + chunkIds.sort().join(',') + modelVersion;
  return crypto.createHash('sha256').update(content).digest('hex');
}

function formatTimestamp(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${minutes}:${secs.toString().padStart(2, '0')}`;
}

function timestampToSeconds(timestamp: string): number {
  const [minutes, seconds] = timestamp.split(':').map(Number);
  return minutes * 60 + seconds;
}

// Cluster chunks within ±90-120s window to reduce redundancy
function clusterChunks(chunks: ChunkResult[]): ChunkResult[] {
  if (chunks.length === 0) return chunks;
  
  const grouped: { [key: string]: ChunkResult[] } = {};
  
  // Group by video_id
  chunks.forEach(chunk => {
    if (!grouped[chunk.video_id]) {
      grouped[chunk.video_id] = [];
    }
    grouped[chunk.video_id].push(chunk);
  });
  
  const clustered: ChunkResult[] = [];
  
  Object.values(grouped).forEach(videoChunks => {
    videoChunks.sort((a, b) => a.start_time_seconds - b.start_time_seconds);
    
    let currentCluster: ChunkResult[] = [];
    
    videoChunks.forEach(chunk => {
      if (currentCluster.length === 0) {
        currentCluster.push(chunk);
      } else {
        const lastChunk = currentCluster[currentCluster.length - 1];
        const timeDiff = Math.abs(chunk.start_time_seconds - lastChunk.end_time_seconds);
        
        if (timeDiff <= 120) { // Within 120 seconds
          currentCluster.push(chunk);
        } else {
          // Finalize current cluster - select best chunk
          const bestChunk = currentCluster.reduce((best, current) => 
            current.similarity > best.similarity ? current : best
          );
          clustered.push(bestChunk);
          
          // Start new cluster
          currentCluster = [chunk];
        }
      }
    });
    
    // Handle final cluster
    if (currentCluster.length > 0) {
      const bestChunk = currentCluster.reduce((best, current) => 
        current.similarity > best.similarity ? current : best
      );
      clustered.push(bestChunk);
    }
  });
  
  return clustered;
}

// Extract keywords from query for better text search
function extractKeywords(query: string): string[] {
  // Remove common question words and extract meaningful terms
  const stopWords = ['how', 'does', 'what', 'why', 'when', 'where', 'who', 'is', 'are', 'can', 'should', 'do', 'the', 'a', 'an', 'to', 'for', 'on', 'in', 'with', 'about', 'recommend', 'recommends'];
  const words = query.toLowerCase()
    .replace(/[?!.,]/g, '')
    .split(/\s+/)
    .filter(word => word.length > 2 && !stopWords.includes(word));
  
  return words;
}

// Generate embeddings for the query
async function generateQueryEmbedding(query: string): Promise<number[]> {
  const EMBEDDING_SERVICE_URL = process.env.EMBEDDING_SERVICE_URL || 'http://localhost:8001';
  
  try {
    console.log('Calling embedding service for query:', query);
    
    const response = await fetch(`${EMBEDDING_SERVICE_URL}/embed`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ text: query }),
      signal: AbortSignal.timeout(10000), // 10 second timeout
    });

    if (!response.ok) {
      console.error('Embedding service error:', response.status);
      return [];
    }

    const data = await response.json();
    console.log(`Generated embedding with ${data.dimensions} dimensions`);
    return data.embedding;
  } catch (error) {
    console.error('Failed to generate query embedding:', error);
    console.log('Falling back to text search');
    return [];
  }
}

// Call LLM to generate answer
async function callSummarizer(query: string, excerpts: ChunkResult[], style: string): Promise<LLMResponse> {
  if (USE_MOCK_MODE) {
    throw new Error('OpenAI API key not configured');
  }

  console.log('Using OpenAI API for answer generation');
  
  const excerptText = excerpts.map((chunk, i) => 
    `- id: ${chunk.video_id}@${formatTimestamp(chunk.start_time_seconds)}\n  date: ${new Date(chunk.published_at).toISOString().split('T')[0]}\n  text: "${chunk.text}"`
  ).join('\n\n');

  // Enhanced word limits for long-form synthesis
  const targetWords = style === 'detailed' ? '800-1200' : '250-400';
  const minWords = style === 'detailed' ? 800 : 250;
  const maxTokens = style === 'detailed' ? 4000 : 1000; // Increased for detailed answers
  
  // System Prompt: Emulated Dr. Chaffee (AI) persona
  const systemPrompt = `# Emulated Dr. Anthony Chaffee (AI) - System Prompt

You are "Emulated Dr. Anthony Chaffee (AI)", speaking in Dr. Chaffee's professional but conversational style.

## Speaking Style (CRITICAL)

- **Professional yet approachable**: Clear and articulate, but not stiff or academic
- **Always use first person**: "I recommend", "I've seen", "What I tell people", "I've found"
- **Be specific, not generic**: Don't say "the carnivore diet focuses on..." - say "When you eat carnivore, you're..."
- Natural speech patterns: "you know", "I mean", "so", "and"
- Complete sentences but conversational flow
- Explain things clearly without being overly formal
- Use contractions naturally: "it's", "you're", "don't", "that's"
- **Avoid third-person descriptions**: Don't describe the diet from outside - speak from experience

## Content Approach

- **ONLY use information from the provided context** - Never add generic medical knowledge
- Get to the point but explain thoroughly
- Use clear, straightforward language
- Share practical examples and observations from YOUR content
- Reference your content naturally: "As I talked about...", "I've mentioned..."
- Be confident and knowledgeable without being preachy
- Acknowledge complexity when relevant
- **If something isn't in your content, say so** - Don't make up answers
- **You advocate for carnivore/animal-based eating** - Never recommend plant foods or tea

## What to AVOID

- ❌ Overly casual: "Look", "Here's the deal", "So basically"
- ❌ Academic formality: "moreover", "furthermore", "in conclusion", "it is important to note"
- ❌ Generic descriptions: "The carnivore diet, which focuses on...", "has been associated with"
- ❌ Third-person narration: "The diet can contribute..." - say "I've seen it help..."
- ❌ Essay structure: No formal introductions or conclusions
- ❌ Hedging language: "One might consider", "It could be argued", "may be beneficial"
- ❌ Overly formal transitions: "Another significant benefit is..."
- ❌ Generic disclaimers: "consult with a healthcare professional", "dietary balance", "individual needs may vary"
- ❌ Hedging conclusions: "In summary", "Overall", "It's important to note"
- ❌ Wishy-washy endings: Don't undermine the message with generic medical disclaimers

## Aim For

- ✅ Natural explanation: "So what happens is...", "The thing is..."
- ✅ Professional but human: "I've found that...", "What we see is..."
- ✅ Clear and direct: Just explain it well without being stuffy`;
  
  // User Prompt: Task and context
  const userPrompt = `You are Emulated Dr. Anthony Chaffee (AI). Answer this question as if you're explaining it to someone in person - professional but natural.

## User Question
${query}

## Retrieved Context (from your videos and talks)

${excerptText}

## Instructions

- **ONLY use information from the retrieved context above** - DO NOT add generic medical knowledge or fill in gaps
- **If the context doesn't cover something, explicitly say so** - "I haven't specifically talked about that" or "I don't have content on that specific topic"
- **NEVER recommend non-carnivore foods** - Dr. Chaffee advocates for animal-based eating only
- **ALWAYS speak in first person**: "I recommend", "I've seen", "What I tell people", "I've found"
- **Be specific, not generic**: Don't describe the diet from outside - share what YOU know from the context
- **Avoid third-person**: Don't say "The carnivore diet is..." - say "When you eat carnivore..." or "I've seen..."
- Natural flow: Use "so", "and", "you know", "I mean" where appropriate
- Avoid academic formality: No "moreover", "furthermore", "in conclusion", "has been associated with"
- Avoid overly casual: No "Look", "Here's the deal", "So basically"
- Cite your videos naturally: "As I talked about at [video_id@mm:ss]"
- **CRITICAL LENGTH: ${targetWords} words (MINIMUM ${minWords} words) - This is NON-NEGOTIABLE**
- ${style === 'detailed' ? 'DETAILED: Elaborate thoroughly with examples, reasoning, and depth. Go into detail on each point.' : 'CONCISE: Be direct but complete'}
- **NO GENERIC CONCLUSIONS**: Don't end with "consult a healthcare professional" or "dietary balance" - that's not your style
- **Be confident**: You know carnivore works - don't hedge or undermine your message at the end
- **CRITICAL: Do not hallucinate or add information not in the context** - Stay true to what Dr. Chaffee actually says

TONE: You're Dr. Chaffee explaining from YOUR experience and knowledge - not describing a diet from outside.
VOICE: First person, specific, professional but natural. NOT generic encyclopedia text.
ENDINGS: End naturally without generic disclaimers or hedging. You're confident in what you're saying.

Output MUST be valid JSON with this schema:
{
  "answer": "Markdown with sections and inline citations like [abc123@12:34]. MUST be ${targetWords} words (minimum ${minWords} words).",
  "citations": [
    { "video_id": "abc123", "timestamp": "12:34", "date": "2024-06-18" }
  ],
  "confidence": 0.0,
  "notes": "Optional brief notes: conflicts seen, gaps, or scope limits."
}

Validation requirements:
- Every [video_id@mm:ss] that appears in answer MUST also appear once in citations[].
- Every citation MUST correspond to an excerpt listed above (exact match or within ±5s).
- Do NOT include citations to sources not present in the excerpts.
- Keep formatting clean: no stray backslashes, no code fences in answer, no HTML.
- If context is too sparse (<8 useful excerpts), create a short answer and explain the limitation in notes.`;

  try {
    const response = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${OPENAI_API_KEY}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        model: SUMMARIZER_MODEL,
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: userPrompt }
        ],
        temperature: 0.3, // Increased for more creative, longer responses
        max_tokens: maxTokens,
        response_format: { type: "json_object" }, // Ensure JSON output
      }),
    });

    if (!response.ok) {
      console.error('OpenAI API error:', response.status, response.statusText);
      throw new Error(`OpenAI API failed: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();
    const content = data.choices[0]?.message?.content;
    
    if (!content) {
      throw new Error('Empty response from OpenAI API');
    }

    try {
      // Extract JSON from the response, handling potential code fences
      let jsonContent = content;
      
      // Check if content is wrapped in code fences and extract just the JSON part
      const jsonMatch = content.match(/```(?:json)?\s*([\s\S]+?)\s*```/);
      if (jsonMatch && jsonMatch[1]) {
        jsonContent = jsonMatch[1].trim();
      }
      
      console.log('Attempting to parse JSON content');
      const parsed = JSON.parse(jsonContent);
      
      // Validate word count
      const wordCount = parsed.answer ? parsed.answer.split(/\s+/).length : 0;
      console.log(`Generated answer: ${wordCount} words (target: ${targetWords}, min: ${minWords})`);
      
      if (wordCount < minWords) {
        console.warn(`⚠️ Answer is too short! Got ${wordCount} words, expected minimum ${minWords}`);
        // Add a note about the shortness
        parsed.notes = (parsed.notes || '') + ` [Warning: Answer only ${wordCount} words, below ${minWords} minimum]`;
      }
      
      console.log('Successfully generated synthesis using OpenAI API');
      return parsed;
    } catch (parseError) {
      console.error('Failed to parse OpenAI response as JSON:', content);
      throw new Error('Invalid JSON response from OpenAI API');
    }
  } catch (error) {
    console.error('OpenAI API call failed:', error);
    throw error;
  }
}


// Validate citations and compute confidence
function validateAndProcessResponse(llmResponse: LLMResponse, chunks: ChunkResult[], query?: string): AnswerResponse {
  const chunkMap = new Map<string, ChunkResult>();
  chunks.forEach(chunk => {
    const key = `${chunk.video_id}@${formatTimestamp(chunk.start_time_seconds)}`;
    chunkMap.set(key, chunk);
  });

  // Validate citations
  const validCitations: Citation[] = [];
  const usedChunkIds: string[] = [];
  
  llmResponse.citations.forEach(citation => {
    const key = `${citation.video_id}@${citation.timestamp}`;
    const chunk = chunkMap.get(key);
    
    if (chunk) {
      validCitations.push({
        video_id: citation.video_id,
        title: chunk.title,
        t_start_s: chunk.start_time_seconds,
        published_at: citation.date,
      });
      usedChunkIds.push(`${chunk.video_id}:${chunk.start_time_seconds}`);
    }
  });

  // Compute confidence heuristic
  let confidence = llmResponse.confidence;
  
  // Adjust based on citation coverage
  const citationCoverage = validCitations.length / llmResponse.citations.length;
  confidence *= citationCoverage;
  
  // Adjust based on chunk quality (average similarity)
  const avgSimilarity = chunks.reduce((sum, chunk) => sum + chunk.similarity, 0) / chunks.length;
  confidence *= Math.min(1.0, avgSimilarity * 2); // Scale similarity to confidence
  
  // Apply confidence boost for well-structured answers with good coverage
  if (chunks.length >= 5 && citationCoverage >= 0.8) {
    // If we have good coverage and enough chunks, boost confidence
    confidence = Math.min(1.0, confidence * 1.15); // 15% boost for well-sourced answers
  }
  
  // Additional boost for answers with high-quality excerpts
  const highQualityExcerpts = chunks.filter(chunk => chunk.similarity > 0.7).length;
  if (highQualityExcerpts >= 3) {
    confidence = Math.min(1.0, confidence * 1.1); // 10% boost for high-quality excerpts
  }
  
  // Adjust based on recency (boost for newer content within last 2 years)
  const now = new Date();
  const recentBonus = chunks.some(chunk => {
    const publishedDate = new Date(chunk.published_at);
    const yearsDiff = (now.getTime() - publishedDate.getTime()) / (1000 * 60 * 60 * 24 * 365);
    return yearsDiff <= 2;
  }) ? 1.1 : 1.0;
  
  confidence = Math.min(1.0, confidence * recentBonus);

  return {
    answer_md: llmResponse.answer,
    citations: validCitations,
    confidence: Math.round(confidence * 100) / 100,
    notes: llmResponse.notes,
    used_chunk_ids: usedChunkIds,
  };
}

// Check answer cache for semantically similar queries
async function checkAnswerCache(query: string, style: string): Promise<any | null> {
  try {
    // Generate embedding for the query
    const embeddingResponse = await fetch(`${BACKEND_API_URL}/embed`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: query })
    });
    
    if (!embeddingResponse.ok) {
      console.warn('Failed to generate embedding for cache lookup');
      return null;
    }
    
    const { embedding, dimensions } = await embeddingResponse.json();
    // Map dimensions to profile and column
    let embeddingProfile: string;
    let embeddingColumn: string;
    if (dimensions === 384) {
      embeddingProfile = 'speed';
      embeddingColumn = 'query_embedding_384';
    } else if (dimensions === 768) {
      embeddingProfile = 'nomic';
      embeddingColumn = 'query_embedding_768';
    } else {
      embeddingProfile = 'quality';
      embeddingColumn = 'query_embedding_1536';
    }
    
    console.log(`[Cache Lookup] Using ${embeddingProfile} profile (${dimensions} dims)`);
    
    // Search for similar cached answers using the appropriate embedding column
    const result = await pool.query(`
      SELECT 
        id,
        query_text,
        answer_md,
        citations,
        confidence,
        notes,
        used_chunk_ids,
        source_clips,
        created_at,
        access_count,
        1 - (${embeddingColumn} <=> $1::vector) as similarity
      FROM answer_cache
      WHERE style = $2
        AND embedding_profile = $3
        AND created_at + (ttl_hours || ' hours')::INTERVAL > NOW()
        AND ${embeddingColumn} IS NOT NULL
        AND 1 - (${embeddingColumn} <=> $1::vector) >= $4
      ORDER BY similarity DESC
      LIMIT 1
    `, [JSON.stringify(embedding), style, embeddingProfile, CACHE_SIMILARITY_THRESHOLD]);
    
    if (result.rows.length > 0) {
      const cached = result.rows[0];
      console.log(`Cache hit: "${cached.query_text}" (similarity: ${(cached.similarity * 100).toFixed(1)}%)`);
      
      // Update access count and timestamp
      await pool.query(`
        UPDATE answer_cache 
        SET accessed_at = NOW(), access_count = access_count + 1
        WHERE id = $1
      `, [cached.id]);
      
      return cached;
    }
    
    return null;
  } catch (error) {
    console.error('Cache lookup error:', error);
    return null; // Fail gracefully
  }
}

// Save answer to cache
async function saveAnswerCache(query: string, style: string, answer: any): Promise<void> {
  try {
    console.log(`[Cache Save] Starting cache save for query: "${query.substring(0, 50)}..." (style: ${style})`);
    
    // Generate embedding for the query
    console.log(`[Cache Save] Fetching embedding from ${BACKEND_API_URL}/embed`);
    const embeddingResponse = await fetch(`${BACKEND_API_URL}/embed`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: query })
    });
    
    if (!embeddingResponse.ok) {
      console.warn('[Cache Save] Failed to generate embedding for cache save, status:', embeddingResponse.status);
      return;
    }
    
    const { embedding, dimensions } = await embeddingResponse.json();
    // Map dimensions to profile and column
    let embeddingProfile: string;
    let embeddingColumn: string;
    if (dimensions === 384) {
      embeddingProfile = 'speed';
      embeddingColumn = 'query_embedding_384';
    } else if (dimensions === 768) {
      embeddingProfile = 'nomic';
      embeddingColumn = 'query_embedding_768';
    } else {
      embeddingProfile = 'quality';
      embeddingColumn = 'query_embedding_1536';
    }
    
    console.log(`[Cache Save] Got embedding: ${dimensions} dims (${embeddingProfile} profile)`);
    
    // Insert into cache with the appropriate embedding column
    console.log('[Cache Save] Inserting into answer_cache table...');
    await pool.query(`
      INSERT INTO answer_cache (
        query_text, ${embeddingColumn}, embedding_profile, style, answer_md, citations, 
        confidence, notes, used_chunk_ids, source_clips, ttl_hours
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
    `, [
      query,
      JSON.stringify(embedding),
      embeddingProfile,
      style,
      answer.answer_md,
      JSON.stringify(answer.citations),
      answer.confidence,
      answer.notes,
      answer.used_chunk_ids,
      JSON.stringify(answer.source_clips || []),
      CACHE_TTL_HOURS
    ]);
    
    console.log(`✅ [Cache Save] Successfully cached answer (${embeddingProfile} profile)`);
  } catch (error) {
    console.error('[Cache Save] Error:', error);
    // Don't fail the request if caching fails
  }
}

// Main API handler
export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'POST' && req.method !== 'GET') {
    // ...
    return res.status(405).json({ error: 'Method not allowed' });
  }

  if (!ANSWER_ENABLED) {
    return res.status(503).json({ error: 'Answer endpoint is disabled' });
  }
  
  // Check if database connection string is configured
  if (!process.env.DATABASE_URL) {
    return res.status(503).json({
      error: 'Database configuration missing',
      message: 'The database connection string is not configured. Please check your environment variables.',
      code: 'DB_CONFIG_MISSING'
    });
  }

  // Parse parameters
  const params = req.method === 'POST' ? req.body : req.query;
  const query = params.q || params.query;
  const maxContext = parseInt(params.max_context as string) || ANSWER_TOPK;
  const maxBullets = parseInt(params.max_bullets as string) || 6;
  const style = (params.style as string) || ANSWER_STYLE_DEFAULT;
  const refresh = params.refresh === '1' || params.refresh === 'true';

  if (!query || typeof query !== 'string' || query.trim().length === 0) {
    return res.status(400).json({ error: 'Query parameter "q" is required' });
  }

  if (!['concise', 'detailed'].includes(style)) {
    return res.status(400).json({ error: 'Style must be "concise" or "detailed"' });
  }

  try {
    console.log('Processing query:', query, 'style:', style);

    // Check cache first (unless refresh is requested)
    if (!refresh) {
      const cachedAnswer = await checkAnswerCache(query, style);
      if (cachedAnswer) {
        console.log('✅ Cache hit! Returning cached answer');
        return res.status(200).json({
          ...cachedAnswer,
          cached: true,
          cache_date: cachedAnswer.created_at
        });
      }
      console.log('Cache miss, generating new answer');
    }

    // DISABLED: Basic RAG service (using sophisticated local method instead)
    // const ragResult = await callRAGService(query);
    // if (ragResult && ragResult.answer) { ... }
    
    // Using sophisticated local method with Chaffee personality emulation
    console.log('Using sophisticated local answer generation with Chaffee personality');

    if (USE_MOCK_MODE) {
      return res.status(503).json({
        error: 'Answer generation unavailable',
        message: 'OpenAI API key not configured. Please configure OPENAI_API_KEY environment variable.',
        code: 'API_KEY_MISSING'
      });
    }

    // Step 2: Embed query and retrieve relevant chunks
    const queryEmbedding = await generateQueryEmbedding(query);
    
    let searchQuery: string;
    let queryParams: any[];
    
    if (queryEmbedding.length > 0) {
      // Semantic search with pgvector
      searchQuery = `
        SELECT 
          seg.id,
          s.id as source_id,
          s.source_id as video_id,
          s.title,
          seg.text,
          seg.start_sec as start_time_seconds,
          seg.end_sec as end_time_seconds,
          s.published_at,
          s.source_type,
          (seg.embedding <=> $1::vector) as similarity
        FROM segments seg
        JOIN sources s ON seg.video_id = s.source_id
        WHERE seg.embedding IS NOT NULL AND seg.speaker_label = 'Chaffee'
        ORDER BY seg.embedding <=> $1::vector
        LIMIT $2
      `;
      queryParams = [JSON.stringify(queryEmbedding), maxContext];
    } else {
      // Fallback to simple text search for reliability
      searchQuery = `
        SELECT 
          seg.id,
          s.id as source_id,
          s.source_id as video_id,
          s.title,
          seg.text,
          seg.start_sec as start_time_seconds,
          seg.end_sec as end_time_seconds,
          s.published_at,
          s.source_type,
          0.5 as similarity
        FROM segments seg
        JOIN sources s ON seg.video_id = s.source_id
        WHERE seg.text ILIKE $1 AND seg.speaker_label = 'Chaffee'
        ORDER BY 
          CASE WHEN seg.text ILIKE $1 THEN 1 ELSE 2 END,
          COALESCE(s.metadata->>'provenance', 'yt_caption') = 'owner' DESC,
          s.published_at DESC,
          seg.start_sec ASC
        LIMIT $2
      `;
      queryParams = [`%${query}%`, maxContext];
    }

    const searchResult = await pool.query(searchQuery, queryParams);
    let chunks: ChunkResult[] = searchResult.rows;
    
    if (chunks.length < 1) {
      return res.status(200).json({ 
        error: 'Insufficient content available',
        message: `Only found ${chunks.length} relevant clips. Need at least 1 clip to generate an answer.`,
        available_chunks: chunks.length,
        code: 'INSUFFICIENT_CONTENT'
      });
    }

    // Apply clustering and ranking
    chunks = chunks.map(chunk => ({
      ...chunk,
      similarity: Math.abs(chunk.similarity)
    }));

    chunks = chunks.map(chunk => {
      let boost = 1.0;
      const publishedDate = new Date(chunk.published_at);
      const now = new Date();
      const yearsDiff = (now.getTime() - publishedDate.getTime()) / (1000 * 60 * 60 * 24 * 365);
      if (yearsDiff <= 1) boost += 0.1;
      else if (yearsDiff <= 2) boost += 0.05;
      if (chunk.source_type === 'youtube') boost += 0.05;
      
      return {
        ...chunk,
        similarity: Math.min(1.0, chunk.similarity * boost)
      };
    });

    chunks.sort((a, b) => b.similarity - a.similarity);
    const clusteredChunks = clusterChunks(chunks.slice(0, maxContext));
    
    if (clusteredChunks.length === 0) {
      return res.status(200).json({ 
        error: 'No relevant content found',
        message: 'Could not find any relevant content after processing and clustering.',
        code: 'NO_RELEVANT_CONTENT'
      });
    }

    // Generate and validate answer
    const llmResponse = await callSummarizer(query, clusteredChunks, style);
    const validatedResponse = validateAndProcessResponse(llmResponse, clusteredChunks, query);

    // Prepare response
    const responseData = {
      ...validatedResponse,
      source_clips: clusteredChunks,
      cached: false,
      total_chunks_considered: chunks.length,
      chunks_after_clustering: clusteredChunks.length,
    };

    // Cache the result for future queries
    await saveAnswerCache(query, style, responseData);
    
    // Return response with source clips
    res.status(200).json(responseData);

  } catch (error) {
    console.error('Answer generation error:', error);
    
    if (error instanceof Error) {
      // Rate limit errors
      if (error.message.includes('429')) {
        return res.status(429).json({
          error: 'Rate limit exceeded',
          message: 'OpenAI API rate limit reached. Please try again in a few moments.',
          code: 'RATE_LIMIT_EXCEEDED'
        });
      }
      
      // Authentication errors
      if (error.message.includes('401')) {
        return res.status(401).json({
          error: 'API authentication failed',
          message: 'OpenAI API key is invalid or expired.',
          code: 'INVALID_API_KEY'
        });
      }
      
      // Database connection errors
      if (error.message.includes('connect') || 
          error.message.includes('ECONNREFUSED') || 
          error.message.includes('database') ||
          error.message.includes('Connection') ||
          error.message.includes('pool')) {
        return res.status(503).json({
          error: 'Database connection failed',
          message: 'Unable to connect to the database. The service may be temporarily unavailable.',
          code: 'DB_CONNECTION_ERROR'
        });
      }
    }
    
    // Generic error handler
    res.status(500).json({ 
      error: 'Answer generation failed',
      message: error instanceof Error ? error.message : 'An unexpected error occurred.',
      code: 'GENERATION_FAILED'
    });
  }
}
