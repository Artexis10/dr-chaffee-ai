/**
 * Tuning Data Hooks
 * 
 * Centralized hooks for fetching and caching tuning metadata.
 * Reduces duplicate API calls across tuning dashboard pages.
 * 
 * Features:
 * - Module-level cache with 30-second TTL
 * - Shared data across components
 * - Manual refresh with ?refresh=true
 * - Loading and error states
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { apiFetch } from '../utils/api';
import type { RAGModelInfo, RagProfile } from '../types/models';
import { FALLBACK_RAG_MODELS } from '../types/models';

// =============================================================================
// Cache Configuration
// =============================================================================

const CACHE_TTL_MS = 30_000; // 30 seconds

interface CacheEntry<T> {
  data: T;
  timestamp: number;
  promise?: Promise<T>;
}

// Module-level cache (shared across all hook instances)
const cache: Record<string, CacheEntry<unknown>> = {};

function getCached<T>(key: string): T | null {
  const entry = cache[key] as CacheEntry<T> | undefined;
  if (!entry) return null;
  
  const age = Date.now() - entry.timestamp;
  if (age > CACHE_TTL_MS) {
    delete cache[key];
    return null;
  }
  
  return entry.data;
}

function setCache<T>(key: string, data: T): void {
  cache[key] = { data, timestamp: Date.now() };
}

function invalidateCache(key: string): void {
  delete cache[key];
}

// =============================================================================
// Generic Hook Factory
// =============================================================================

interface UseTuningDataResult<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

function useTuningData<T>(
  cacheKey: string,
  fetchUrl: string,
  fallback: T | null = null
): UseTuningDataResult<T> {
  const [data, setData] = useState<T | null>(() => getCached<T>(cacheKey) || fallback);
  const [loading, setLoading] = useState(!getCached<T>(cacheKey));
  const [error, setError] = useState<string | null>(null);
  const mountedRef = useRef(true);

  const fetchData = useCallback(async (forceRefresh = false) => {
    // Check cache first (unless forcing refresh)
    if (!forceRefresh) {
      const cached = getCached<T>(cacheKey);
      if (cached) {
        setData(cached);
        setLoading(false);
        return;
      }
    }

    setLoading(true);
    setError(null);

    try {
      const url = forceRefresh ? `${fetchUrl}?refresh=true` : fetchUrl;
      const res = await apiFetch(url);
      
      if (!res.ok) {
        if (res.status === 401) {
          throw new Error('Authentication required');
        }
        throw new Error(`Failed to fetch: ${res.status}`);
      }
      
      const result = await res.json();
      
      if (mountedRef.current) {
        setData(result);
        setCache(cacheKey, result);
        setError(null);
      }
    } catch (err) {
      console.warn(`[useTuningData] ${cacheKey} fetch failed:`, err);
      if (mountedRef.current) {
        setError(err instanceof Error ? err.message : 'Failed to fetch');
        // Keep existing data or fallback on error
        if (!data && fallback) {
          setData(fallback);
        }
      }
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [cacheKey, fetchUrl, fallback, data]);

  useEffect(() => {
    mountedRef.current = true;
    fetchData();
    return () => {
      mountedRef.current = false;
    };
  }, [fetchData]);

  const refresh = useCallback(async () => {
    invalidateCache(cacheKey);
    await fetchData(true);
  }, [cacheKey, fetchData]);

  return { data, loading, error, refresh };
}

// =============================================================================
// Specific Hooks
// =============================================================================

/**
 * Hook for RAG models (used in profiles page for model selection).
 */
export function useRagModels(): UseTuningDataResult<RAGModelInfo[]> {
  return useTuningData<RAGModelInfo[]>(
    'tuning/models/rag',
    '/api/tuning/models/rag',
    FALLBACK_RAG_MODELS
  );
}

/**
 * Hook for summarizer models (used in models page).
 */
export interface SummarizerModel {
  key: string;
  name: string;
  provider: string;
  quality_tier: string;
  cost_input: string;
  cost_output: string;
  speed: string;
  recommended: boolean;
  pros: string[];
  cons: string[];
  description: string;
}

export interface SummarizerModelsData {
  active_model_name: string;  // Primary field from backend
  current_model: string;  // Legacy field for backwards compatibility
  models: Record<string, Omit<SummarizerModel, 'key'>>;
}

export function useSummarizerModels(): UseTuningDataResult<SummarizerModelsData> {
  return useTuningData<SummarizerModelsData>(
    'tuning/summarizer/models',
    '/api/tuning/summarizer/models',
    null
  );
}

/**
 * Hook for RAG profiles.
 */
export function useProfiles(): UseTuningDataResult<RagProfile[]> {
  return useTuningData<RagProfile[]>(
    'tuning/profiles',
    '/api/tuning/profiles',
    []
  );
}

/**
 * Hook for search configuration.
 */
export interface SearchConfig {
  top_k: number;
  min_similarity: number;
  enable_reranker: boolean;
  rerank_top_k: number;
  return_top_k: number;
}

export interface SearchConfigResponse {
  config: SearchConfig | null;
  error: string | null;
  error_code: string | null;
}

export function useSearchConfig(): UseTuningDataResult<SearchConfigResponse> {
  return useTuningData<SearchConfigResponse>(
    'tuning/search-config',
    '/api/tuning/search-config',
    { config: null, error: null, error_code: null }
  );
}

/**
 * Hook for custom instructions.
 */
export interface CustomInstruction {
  id?: number;
  name: string;
  instructions: string;
  description?: string;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
  version?: number;
}

export function useInstructions(): UseTuningDataResult<CustomInstruction[]> {
  return useTuningData<CustomInstruction[]>(
    'tuning/instructions',
    '/api/tuning/instructions',
    []
  );
}

/**
 * Check if user is authenticated for tuning dashboard.
 * 
 * Uses dedicated /api/tuning/auth/status endpoint which:
 * - Checks the tuning_auth cookie locally (no backend call)
 * - Returns { hasAccess: boolean }
 * 
 * The refresh() function can be called after login to re-check auth status.
 */
export function useTuningAuth(): { 
  isAuthenticated: boolean; 
  loading: boolean; 
  refresh: () => void;
} {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    let mounted = true;

    const checkAuth = async () => {
      try {
        // Use dedicated status endpoint - fast local check, no backend call
        const res = await apiFetch('/api/tuning/auth/status');
        if (mounted && res.ok) {
          const data = await res.json();
          setIsAuthenticated(data.hasAccess === true);
        } else if (mounted) {
          setIsAuthenticated(false);
        }
      } catch {
        if (mounted) {
          setIsAuthenticated(false);
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };

    checkAuth();
    return () => {
      mounted = false;
    };
  }, [refreshKey]);

  // Trigger a re-check of auth status (call after login)
  const refresh = useCallback(() => {
    setLoading(true);
    setRefreshKey(k => k + 1);
  }, []);

  return { isAuthenticated, loading, refresh };
}

// =============================================================================
// Cache Utilities (for manual invalidation after mutations)
// =============================================================================

/**
 * Invalidate a specific cache entry.
 */
export function invalidateTuningCache(key: 'profiles' | 'search-config' | 'instructions' | 'models/rag' | 'summarizer/models'): void {
  invalidateCache(`tuning/${key}`);
}

/**
 * Invalidate all tuning caches.
 */
export function invalidateAllTuningCaches(): void {
  Object.keys(cache).forEach(key => {
    if (key.startsWith('tuning/')) {
      delete cache[key];
    }
  });
}
