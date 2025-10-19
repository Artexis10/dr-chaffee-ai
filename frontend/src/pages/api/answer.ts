import { NextApiRequest, NextApiResponse } from 'next';
import { Pool } from 'pg';
import * as crypto from 'crypto';

// Configure API route for longer timeouts (needed for detailed answers)
// Note: maxDuration only works on Vercel. For Render/self-hosted, configure timeout in platform settings.
export const config = {
  api: {
    responseLimit: false,
    bodyParser: {
      sizeLimit: '10mb',
    },
  },
  // maxDuration: 180, // Only for Vercel - commented out for Render deployment
};

// Database connection
const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false
});

// Configuration
const ANSWER_ENABLED = process.env.ANSWER_ENABLED !== 'false'; // Default to enabled
const ANSWER_TOPK = parseInt(process.env.ANSWER_TOPK || '100'); // Number of chunks to retrieve (increased for better coverage)
const ANSWER_TTL_HOURS = parseInt(process.env.ANSWER_TTL_HOURS || '336'); // 14 days
const SUMMARIZER_MODEL = process.env.SUMMARIZER_MODEL || 'gpt-4o-mini'; // Default to gpt-4o-mini: faster, cheaper, better than gpt-3.5-turbo
const ANSWER_STYLE_DEFAULT = process.env.ANSWER_STYLE_DEFAULT || 'concise';
const OPENAI_API_KEY = process.env.OPENAI_API_KEY;
const USE_MOCK_MODE = !OPENAI_API_KEY || OPENAI_API_KEY.includes('your_') || process.env.USE_MOCK_MODE === 'true';

// Clip limits per style (to prevent token overflow and control context size)
const MAX_CLIPS_CONCISE = parseInt(process.env.MAX_CLIPS_CONCISE || '30'); // Concise: fewer clips, focused answer
const MAX_CLIPS_DETAILED = parseInt(process.env.MAX_CLIPS_DETAILED || '50'); // Detailed: more clips, comprehensive answer

console.log('ANSWER_ENABLED:', ANSWER_ENABLED);
console.log('USE_MOCK_MODE:', USE_MOCK_MODE);

// Backend API Integration
const BACKEND_API_URL = process.env.BACKEND_API_URL || process.env.EMBEDDING_SERVICE_URL || 'https://drchaffee-backend.onrender.com';

// Cache configuration
const CACHE_SIMILARITY_THRESHOLD = 0.92; // 92% similarity to consider a cache hit
const CACHE_TTL_HOURS = parseInt(process.env.ANSWER_CACHE_TTL_HOURS || '336'); // 14 days

// Rate limiting configuration (per-style limits)
const RATE_LIMIT_WINDOW_MS = 60 * 1000; // 1 minute window
const RATE_LIMIT_CONCISE = parseInt(process.env.RATE_LIMIT_CONCISE || '10'); // 10 concise answers per minute
const RATE_LIMIT_DETAILED = parseInt(process.env.RATE_LIMIT_DETAILED || '3'); // 3 detailed answers per minute (more expensive)

// In-memory rate limit tracking (use Redis in production for multi-instance deployments)
const rateLimitMap = new Map<string, { concise: number[], detailed: number[] }>();

function checkRateLimit(clientId: string, style: 'concise' | 'detailed'): { allowed: boolean; retryAfter?: number } {
  const now = Date.now();
  const limit = style === 'detailed' ? RATE_LIMIT_DETAILED : RATE_LIMIT_CONCISE;
  
  // Get or create client record
  if (!rateLimitMap.has(clientId)) {
    rateLimitMap.set(clientId, { concise: [], detailed: [] });
  }
  
  const clientRecord = rateLimitMap.get(clientId)!;
  const requests = clientRecord[style];
  
  // Remove requests outside the window
  const validRequests = requests.filter(timestamp => now - timestamp < RATE_LIMIT_WINDOW_MS);
  clientRecord[style] = validRequests;
  
  // Check if limit exceeded
  if (validRequests.length >= limit) {
    const oldestRequest = Math.min(...validRequests);
    const retryAfter = Math.ceil((oldestRequest + RATE_LIMIT_WINDOW_MS - now) / 1000);
    return { allowed: false, retryAfter };
  }
  
  // Add current request
  validRequests.push(now);
  return { allowed: true };
}

// Cleanup old entries periodically (every 5 minutes)
setInterval(() => {
  const now = Date.now();
  for (const [clientId, record] of Array.from(rateLimitMap.entries())) {
    record.concise = record.concise.filter((t: number) => now - t < RATE_LIMIT_WINDOW_MS);
    record.detailed = record.detailed.filter((t: number) => now - t < RATE_LIMIT_WINDOW_MS);
    
    // Remove empty records
    if (record.concise.length === 0 && record.detailed.length === 0) {
      rateLimitMap.delete(clientId);
    }
  }
}, 5 * 60 * 1000);

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
  // Always use mm:ss format (YouTube style) - never h:mm:ss
  // This prevents confusion: 71:21 is clearer than 1:11:21
  const totalMinutes = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  
  return `${totalMinutes}:${secs.toString().padStart(2, '0')}`;
}

function timestampToSeconds(timestamp: string): number {
  const parts = timestamp.split(':').map(Number);
  if (parts.length === 3) {
    // Could be HH:MM:SS or MM:SS with leading zero
    // If first part > 23, treat as MM:SS (e.g., 71:21:00 is invalid)
    const [first, second, third] = parts;
    if (first > 23) {
      // Treat as MM:SS:00 (malformed) - use first two parts
      return first * 60 + second;
    }
    // Valid HH:MM:SS
    return first * 3600 + second * 60 + third;
  } else if (parts.length === 2) {
    // MM:SS format (standard YouTube format)
    const [minutes, seconds] = parts;
    return minutes * 60 + seconds;
  }
  return 0;
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

  console.log(`[callSummarizer] Generating ${style} answer with ${excerpts.length} chunks`);
  
  // Limit chunks based on style to prevent token overflow and control context size
  // Estimate: ~150 tokens per chunk, system prompt ~500, user prompt ~300
  const maxChunks = style === 'detailed' ? MAX_CLIPS_DETAILED : MAX_CLIPS_CONCISE;
  const limitedExcerpts = excerpts.slice(0, maxChunks);
  
  if (excerpts.length > maxChunks) {
    console.log(`[callSummarizer] ⚠️ Limiting from ${excerpts.length} to ${maxChunks} chunks (${style} style limit)`);
  }
  
  const excerptText = limitedExcerpts.map((chunk, i) => 
    `- id: ${chunk.video_id}@${formatTimestamp(chunk.start_time_seconds)}\n  date: ${new Date(chunk.published_at).toISOString().split('T')[0]}\n  text: "${chunk.text}"`
  ).join('\n\n');
  
  // Calculate approximate token count (rough estimate: 1 token ≈ 4 characters)
  const estimatedInputTokens = Math.ceil((excerptText.length + 3000) / 4);
  console.log(`[callSummarizer] Estimated input tokens: ~${estimatedInputTokens}`);

  // Word limits optimized for quality and speed (Render Starter 60s timeout)
  // Short: ~400 words (focused, efficient)
  // Long: ~800 words (comprehensive, detailed) - 2x the length of short
  const targetWords = style === 'detailed' ? '750-850' : '350-450';
  const minWords = style === 'detailed' ? 750 : 350;
  const maxTokens = style === 'detailed' ? 2800 : 1400; // gpt-4o-mini generates ~20-30s
  
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
- **CITATION FORMAT (CRITICAL)**: Use SQUARE BRACKETS [video_id@mm:ss], NOT parentheses. Example: "As I talked about [abc123@12:34]" or "I've discussed this [xyz789@45:12]"
- **CRITICAL LENGTH: ${targetWords} words (MINIMUM ${minWords} words) - This is ABSOLUTELY NON-NEGOTIABLE**
- ${style === 'detailed' ? 'DETAILED MODE: Write a COMPREHENSIVE response (750-850 words). Use 2-3 clear sections with markdown headings (## Heading). Each section should have 2-3 paragraphs of 4-6 sentences each. Cover the topic thoroughly with proper structure.' : 'CONCISE MODE: Write a TIGHT, FOCUSED response (350-450 words). NO HEADINGS. Write as ONE OR TWO substantial paragraphs ONLY. Each paragraph must be 6-8 sentences minimum. Do NOT break into multiple short paragraphs. Keep it flowing and cohesive.'}
- **PARAGRAPH STRUCTURE**: ${style === 'detailed' ? 'Combine related ideas into cohesive paragraphs - Each paragraph should be 4-6 sentences minimum.' : 'CRITICAL: Write as ONE continuous paragraph or maximum TWO paragraphs. Do NOT create 3+ paragraphs. Keep the response flowing without breaks.'}
- **FLOW AND COHESION**: Topics should flow logically, not jump around. Develop each idea fully before moving on. Use transitions between paragraphs.
- **AVOID REPETITIVE TRANSITIONS**: Don't start every paragraph with "I've found", "In my experience", "I've seen" - vary your language naturally.
- **NO GENERIC CONCLUSIONS**: Don't end with "consult a healthcare professional" or "dietary balance" - that's not your style
- **Be confident**: You know carnivore works - don't hedge or undermine your message at the end
- **CRITICAL: Do not hallucinate or add information not in the context** - Stay true to what Dr. Chaffee actually says

TONE: You're Dr. Chaffee explaining from YOUR experience and knowledge - not describing a diet from outside.
VOICE: First person, specific, professional but natural. NOT generic encyclopedia text.
ENDINGS: End naturally without generic disclaimers or hedging. You're confident in what you're saying.

Output MUST be valid **JSON RESPONSE FORMAT** (CRITICAL - MUST be valid JSON):
{
  "answer": "Markdown with sections and inline citations like [abc123@12:34]. MUST be ${targetWords} words (minimum ${minWords} words).",
  "citations": [
    { "video_id": "abc123", "timestamp": "12:34", "date": "2024-06-18" }
  ],
  "confidence": 0.85,
  "notes": "Optional brief notes: conflicts seen, gaps, or scope limits."
}

**CRITICAL CITATION FORMAT**: 
- **USE SQUARE BRACKETS ONLY**: [video_id@mm:ss] NOT (video_id@mm:ss) or any other format
- Video IDs must be EXACTLY as shown in the context (e.g., "prSNurxY5ic" not "prSNurxY5j")
- Timestamps MUST use MM:SS format (e.g., "76:13" for 76 minutes 13 seconds, NOT "1:16:13")
- For videos longer than 60 minutes, use total minutes (e.g., "71:21" not "1:11:21")
- Copy timestamps EXACTLY as shown in the context excerpts
- Double-check every video_id and timestamp character-by-character
- Example: "As I discussed [vKiUYeKpHDs@36:56], the connection is clear"

**CONFIDENCE SCORING**:
- Set confidence between 0.7-0.95 based on context quality
- 0.9-0.95: Excellent coverage with many relevant excerpts
- 0.8-0.89: Good coverage with solid excerpts
- 0.7-0.79: Adequate coverage but some gaps
Validation requirements:
- Every [video_id@mm:ss] that appears in answer MUST also appear once in citations[].
- Every citation MUST correspond to an excerpt listed above (exact match or within ±5s).
- **VIDEO IDs MUST BE EXACT**: Copy video_id character-by-character from context. Do NOT modify.
- Do NOT include citations to sources not present in the excerpts.
- Keep formatting clean: no stray backslashes, no code fences in answer, no HTML.
- **MEET THE WORD COUNT**: ${minWords}+ words is mandatory. Write more content, not less.
- If context is too sparse (<8 useful excerpts), still aim for target length by elaborating on available content.`;

  try {
    console.log(`[callSummarizer] Calling OpenAI API with model: ${SUMMARIZER_MODEL}`);
    console.log(`[callSummarizer] Max output tokens: ${maxTokens}`);
    
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
      const errorBody = await response.text();
      console.error('[callSummarizer] OpenAI API error:', response.status, response.statusText);
      console.error('[callSummarizer] Error body:', errorBody);
      throw new Error(`OpenAI API failed: ${response.status} ${response.statusText} - ${errorBody}`);
    }

    const data = await response.json();
    
    // Log token usage
    if (data.usage) {
      console.log(`[callSummarizer] Token usage - Input: ${data.usage.prompt_tokens}, Output: ${data.usage.completion_tokens}, Total: ${data.usage.total_tokens}`);
    }
    
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
      
      console.log('[callSummarizer] Attempting to parse JSON content');
      const parsed = JSON.parse(jsonContent);
      
      // Validate word count
      const wordCount = parsed.answer ? parsed.answer.split(/\s+/).length : 0;
      console.log(`[callSummarizer] Generated answer: ${wordCount} words (target: ${targetWords}, min: ${minWords})`);
      
      // Calculate how far off we are from target
      const minTarget = parseInt(targetWords.split('-')[0]);
      const maxTarget = parseInt(targetWords.split('-')[1]);
      
      if (wordCount < minWords * 0.5) {
        // Severely short - less than 50% of minimum
        console.error(`[callSummarizer] ❌ Answer is SEVERELY short! Got ${wordCount} words, expected minimum ${minWords}`);
        parsed.notes = (parsed.notes || '') + ` [CRITICAL: Answer only ${wordCount} words, expected ${minWords}+ words]`;
      } else if (wordCount < minWords) {
        // Somewhat short but acceptable
        console.warn(`[callSummarizer] ⚠️ Answer is short. Got ${wordCount} words, expected minimum ${minWords}`);
        parsed.notes = (parsed.notes || '') + ` [Note: Answer ${wordCount} words, target was ${minWords}+ words]`;
      } else if (wordCount >= minTarget && wordCount <= maxTarget) {
        // Perfect range
        console.log(`[callSummarizer] ✅ Answer length is perfect: ${wordCount} words in target range ${targetWords}`);
      } else if (wordCount > maxTarget) {
        // Over target but that's fine
        console.log(`[callSummarizer] ✅ Answer is comprehensive: ${wordCount} words (above target ${targetWords})`);
      }
      
      console.log('[callSummarizer] ✅ Successfully generated synthesis using OpenAI API');
      return parsed;
    } catch (parseError) {
      console.error('[callSummarizer] Failed to parse OpenAI response as JSON:', content);
      console.error('[callSummarizer] Parse error:', parseError);
      throw new Error('Invalid JSON response from OpenAI API');
    }
  } catch (error) {
    console.error('[callSummarizer] OpenAI API call failed:', error);
    if (error instanceof Error) {
      console.error('[callSummarizer] Error details:', error.message);
      console.error('[callSummarizer] Error stack:', error.stack);
    }
    throw error;
  }
}


// Validate citations and compute confidence
function validateAndProcessResponse(llmResponse: LLMResponse, chunks: ChunkResult[], query?: string): AnswerResponse {
  // Build maps for both exact and fuzzy matching
  const chunkMap = new Map<string, ChunkResult>();
  const videoIdMap = new Map<string, ChunkResult[]>();
  
  chunks.forEach(chunk => {
    const key = `${chunk.video_id}@${formatTimestamp(chunk.start_time_seconds)}`;
    chunkMap.set(key, chunk);
    
    // Also index by video_id for fuzzy matching
    if (!videoIdMap.has(chunk.video_id)) {
      videoIdMap.set(chunk.video_id, []);
    }
    videoIdMap.get(chunk.video_id)!.push(chunk);
  });

  // Validate citations
  const validCitations: Citation[] = [];
  const usedChunkIds: string[] = [];
  const malformedCitations: string[] = [];
  
  llmResponse.citations.forEach(citation => {
    const key = `${citation.video_id}@${citation.timestamp}`;
    let chunk = chunkMap.get(key);
    
    // If exact match fails, try fuzzy matching by timestamp
    if (!chunk) {
      // Try to find by video_id and similar timestamp
      const videoChunks = videoIdMap.get(citation.video_id);
      if (videoChunks) {
        // Parse timestamp to seconds
        const timestampParts = citation.timestamp.split(':').map(Number);
        let targetSeconds = 0;
        if (timestampParts.length === 2) {
          targetSeconds = timestampParts[0] * 60 + timestampParts[1];
        } else if (timestampParts.length === 3) {
          targetSeconds = timestampParts[0] * 3600 + timestampParts[1] * 60 + timestampParts[2];
        }
        
        // Find closest chunk within 10 seconds
        chunk = videoChunks.reduce((closest, current) => {
          const currentDiff = Math.abs(current.start_time_seconds - targetSeconds);
          const closestDiff = closest ? Math.abs(closest.start_time_seconds - targetSeconds) : Infinity;
          return currentDiff < closestDiff && currentDiff <= 10 ? current : closest;
        }, null as ChunkResult | null) || undefined;
        
        if (chunk) {
          console.log(`[Citation Fix] Fuzzy matched ${citation.video_id}@${citation.timestamp} to ${chunk.video_id}@${formatTimestamp(chunk.start_time_seconds)}`);
        }
      }
    }
    
    if (chunk) {
      validCitations.push({
        video_id: chunk.video_id, // Use the correct video_id from chunk
        title: chunk.title,
        t_start_s: chunk.start_time_seconds,
        published_at: citation.date,
      });
      usedChunkIds.push(`${chunk.video_id}:${chunk.start_time_seconds}`);
    } else {
      malformedCitations.push(key);
      console.warn(`[Citation Validation] Failed to match citation: ${key}`);
    }
  });
  
  if (malformedCitations.length > 0) {
    console.warn(`[Citation Validation] ${malformedCitations.length} malformed citations:`, malformedCitations.slice(0, 5));
  }

  // Compute confidence heuristic
  let confidence = llmResponse.confidence || 0.8; // Default to 0.8 if LLM returns 0
  
  // If LLM returned 0, calculate from scratch
  if (confidence === 0) {
    console.warn('[validateAndProcessResponse] LLM returned confidence 0, calculating from context quality');
    confidence = 0.7; // Start with baseline
  }
  
  // Adjust based on citation coverage
  const citationCoverage = llmResponse.citations.length > 0 
    ? validCitations.length / llmResponse.citations.length 
    : 0.5;
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
      console.warn('[Cache Lookup] Failed to generate embedding');
      return null;
    }
    
    const { embedding, model_key } = await embeddingResponse.json();
    
    if (!embedding || !model_key) {
      console.warn('[Cache Lookup] Invalid embedding response');
      return null;
    }
    
    console.log(`[Cache Lookup] Using model: ${model_key}`);
    
    // Use the search function to find similar cached answers
    const result = await pool.query(`
      SELECT 
        ac.id,
        ac.query_text,
        ac.answer_md,
        ac.citations,
        ac.confidence,
        ac.notes,
        ac.used_chunk_ids,
        ac.source_clips,
        ac.created_at,
        ac.access_count,
        cache_search.similarity
      FROM search_answer_cache_by_model($1::vector, $2, $3, $4, 1) cache_search
      JOIN answer_cache ac ON ac.id = cache_search.cache_id
      LIMIT 1
    `, [JSON.stringify(embedding), model_key, style, CACHE_SIMILARITY_THRESHOLD]);
    
    if (result.rows.length > 0) {
      const cached = result.rows[0];
      console.log(`✅ [Cache Hit] "${cached.query_text.substring(0, 50)}..." (similarity: ${(cached.similarity * 100).toFixed(1)}%)`);
      
      // Update access count and timestamp
      await pool.query(`
        UPDATE answer_cache 
        SET accessed_at = NOW(), access_count = access_count + 1
        WHERE id = $1
      `, [cached.id]);
      
      return cached;
    }
    
    console.log('[Cache Lookup] No cache hit found');
    return null;
  } catch (error) {
    console.error('❌ [Cache Lookup] Error:', error);
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
      const errorText = await embeddingResponse.text();
      console.error('[Cache Save] Failed to generate embedding, status:', embeddingResponse.status, 'error:', errorText);
      return;
    }
    
    const embeddingData = await embeddingResponse.json();
    const { embedding, model_key } = embeddingData;
    
    if (!embedding || !model_key) {
      console.error('[Cache Save] Invalid embedding response - missing embedding or model_key');
      return;
    }
    
    console.log(`[Cache Save] Got embedding for model: ${model_key}`);
    
    // Insert into answer_cache table (without embedding)
    console.log('[Cache Save] Inserting into answer_cache table...');
    
    const insertResult = await pool.query(`
      INSERT INTO answer_cache (
        query_text, style, answer_md, citations, 
        confidence, notes, used_chunk_ids, source_clips, ttl_hours
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
      RETURNING id
    `, [
      query,
      style,
      answer.answer_md,
      JSON.stringify(answer.citations),
      answer.confidence,
      answer.notes,
      answer.used_chunk_ids,
      JSON.stringify(answer.source_clips || []),
      CACHE_TTL_HOURS
    ]);
    
    const cacheId = insertResult.rows[0]?.id;
    
    // Insert embedding into answer_cache_embeddings table
    await pool.query(`
      INSERT INTO answer_cache_embeddings (
        answer_cache_id, model_key, embedding
      ) VALUES ($1, $2, $3::vector)
    `, [cacheId, model_key, JSON.stringify(embedding)]);
    
    console.log(`✅ [Cache Save] Successfully cached answer (model: ${model_key}), cache ID: ${cacheId}`);
  } catch (error) {
    console.error('❌ [Cache Save] Failed to save to answer_cache');
    console.error('[Cache Save] Error:', error);
    if (error instanceof Error) {
      console.error('[Cache Save] Error message:', error.message);
      console.error('[Cache Save] Error stack:', error.stack);
    }
    // Log the data that failed to insert (for debugging)
    console.error('[Cache Save] Failed data:', {
      query: query.substring(0, 100),
      style,
      answerLength: answer.answer_md?.length,
      citationsCount: answer.citations?.length,
      confidence: answer.confidence
    });
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
  const maxContext = parseInt(params.max_context as string) || parseInt(params.top_k as string) || ANSWER_TOPK;
  const maxBullets = parseInt(params.max_bullets as string) || 6;
  const style = (params.style as string) || ANSWER_STYLE_DEFAULT;
  const refresh = params.refresh === '1' || params.refresh === 'true';
  
  console.log(`[Answer API] Query: "${query}", maxContext: ${maxContext}, style: ${style}`);

  if (!query || typeof query !== 'string' || query.trim().length === 0) {
    return res.status(400).json({ error: 'Query parameter "q" is required' });
  }

  if (!['concise', 'detailed'].includes(style)) {
    return res.status(400).json({ error: 'Style must be "concise" or "detailed"' });
  }

  // Check rate limit (use IP address as client ID)
  let clientId = 'unknown';
  let rateLimitCheck: { allowed: boolean; retryAfter?: number } = { allowed: true };
  
  try {
    clientId = req.headers['x-forwarded-for'] as string || req.socket.remoteAddress || 'unknown';
    rateLimitCheck = checkRateLimit(clientId, style as 'concise' | 'detailed');
    
    if (!rateLimitCheck.allowed) {
      console.log(`[Answer API] Rate limit exceeded for ${clientId}, style: ${style}`);
      return res.status(429).json({
        error: 'Rate limit exceeded',
        message: `Too many ${style} answer requests. Please try again in ${rateLimitCheck.retryAfter} seconds.`,
        retryAfter: rateLimitCheck.retryAfter,
        limit: style === 'detailed' ? RATE_LIMIT_DETAILED : RATE_LIMIT_CONCISE,
        window: '1 minute'
      });
    }
  } catch (rateLimitError) {
    console.error('[Answer API] Rate limit check failed:', rateLimitError);
    // Continue anyway - don't block requests if rate limiting fails
  }

  try {
    console.log(`[Answer API] Processing query: "${query}", style: ${style}, refresh: ${refresh}`);
    console.log(`[Answer API] Client ID: ${clientId}`);
    console.log(`[Answer API] Rate limit passed for ${style} style`);

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
    console.log(`[Answer API] Generating embedding for query...`);
    const queryEmbedding = await generateQueryEmbedding(query);
    console.log(`[Answer API] Embedding generated: ${queryEmbedding.length} dimensions`);
    
    let searchQuery: string;
    let queryParams: any[];
    
    if (queryEmbedding.length > 0) {
      // Determine which model to use based on embedding dimensions
      let modelKey = 'nomic-v1.5';
      if (queryEmbedding.length === 384) {
        modelKey = 'all-minilm-l6-v2';
      } else if (queryEmbedding.length === 1536) {
        modelKey = 'gte-qwen2-1.5b';
      }
      
      console.log(`[Answer API] Using model: ${modelKey} (${queryEmbedding.length} dims)`);
      
      // Try segment_embeddings table first (normalized storage)
      searchQuery = `
        SELECT 
          se.segment_id as id,
          s.id as source_id,
          s.source_id as video_id,
          s.title,
          seg.text,
          seg.start_sec as start_time_seconds,
          seg.end_sec as end_time_seconds,
          s.published_at,
          s.source_type,
          1 - (se.embedding <=> $1::vector) as similarity
        FROM segment_embeddings se
        JOIN segments seg ON se.segment_id = seg.id
        JOIN sources s ON seg.video_id = s.source_id
        WHERE se.embedding IS NOT NULL 
          AND se.model_key = $3
          AND seg.speaker_label = 'Chaffee'
        ORDER BY se.embedding <=> $1::vector
        LIMIT $2
      `;
      queryParams = [JSON.stringify(queryEmbedding), maxContext, modelKey];
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

    let searchResult = await pool.query(searchQuery, queryParams);
    let chunks: ChunkResult[] = searchResult.rows;
    
    console.log(`[Answer API] Initial retrieval: ${chunks.length} chunks`);
    
    // Fallback: If segment_embeddings returned no results, try legacy segments.embedding column
    if (chunks.length === 0 && queryEmbedding.length > 0) {
      console.log(`[Answer API] No results from segment_embeddings, trying legacy segments.embedding...`);
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
          1 - (seg.embedding <=> $1::vector) as similarity
        FROM segments seg
        JOIN sources s ON seg.video_id = s.source_id
        WHERE seg.embedding IS NOT NULL 
          AND seg.speaker_label = 'Chaffee'
        ORDER BY seg.embedding <=> $1::vector
        LIMIT $2
      `;
      searchResult = await pool.query(searchQuery, [JSON.stringify(queryEmbedding), maxContext]);
      chunks = searchResult.rows;
      console.log(`[Answer API] Legacy retrieval: ${chunks.length} chunks`);
    }
    
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
    
    // Take top chunks without aggressive clustering (semantic search already handles relevance)
    const topChunks = chunks.slice(0, maxContext);
    
    console.log(`[Answer API] Final chunks for summarization: ${topChunks.length}`);
    console.log(`[Answer API] Similarity range: ${topChunks.length > 0 ? `${topChunks[0].similarity.toFixed(3)} - ${topChunks[topChunks.length - 1].similarity.toFixed(3)}` : 'N/A'}`);
    
    if (topChunks.length === 0) {
      return res.status(200).json({ 
        error: 'No relevant content found',
        message: 'Could not find any relevant content.',
        code: 'NO_RELEVANT_CONTENT'
      });
    }

    // Generate and validate answer
    const llmResponse = await callSummarizer(query, topChunks, style);
    const validatedResponse = validateAndProcessResponse(llmResponse, topChunks, query);

    // Prepare response
    const responseData = {
      ...validatedResponse,
      source_clips: topChunks,
      cached: false,
      total_chunks_considered: chunks.length,
      chunks_used: topChunks.length,
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
    
    // Generic error handler - log full error for debugging
    console.error('❌ [Answer API] Unhandled error:', error);
    if (error instanceof Error) {
      console.error('[Answer API] Error stack:', error.stack);
    }
    
    res.status(500).json({ 
      error: 'Answer generation failed',
      message: error instanceof Error ? error.message : 'An unexpected error occurred.',
      code: 'GENERATION_FAILED',
      details: process.env.NODE_ENV === 'development' ? (error instanceof Error ? error.stack : String(error)) : undefined
    });
  }
}
