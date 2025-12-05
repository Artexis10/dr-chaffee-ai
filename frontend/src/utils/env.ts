/**
 * Environment Variable Utilities
 * 
 * Centralized access to environment variables with validation and logging.
 * All API routes should use these helpers instead of accessing process.env directly.
 */

/**
 * Backend API URL - used by Next.js API routes to proxy requests to the FastAPI backend.
 * 
 * In production (Vercel): Should be set to https://app.askdrchaffee.com
 * In development: Defaults to http://localhost:8000
 */
export const BACKEND_API_URL = process.env.BACKEND_API_URL || 'http://localhost:8000';

/**
 * Internal API key for backend authentication.
 * Must match the INTERNAL_API_KEY set on the backend.
 */
export const INTERNAL_API_KEY = process.env.INTERNAL_API_KEY || '';

/**
 * Log environment configuration on first import (server-side only).
 * This helps debug deployment issues.
 */
if (typeof window === 'undefined') {
  // Only log on server-side, and only once
  const hasLogged = (global as any).__envLogged;
  if (!hasLogged) {
    (global as any).__envLogged = true;
    console.log('[ENV] BACKEND_API_URL:', BACKEND_API_URL ? `${BACKEND_API_URL.substring(0, 30)}...` : 'NOT SET');
    console.log('[ENV] INTERNAL_API_KEY:', INTERNAL_API_KEY ? 'SET (hidden)' : 'NOT SET');
  }
}

/**
 * Validate that required environment variables are set.
 * Call this at the start of API routes that need these values.
 */
export function validateEnv(): { valid: boolean; missing: string[] } {
  const missing: string[] = [];
  
  if (!process.env.BACKEND_API_URL) {
    missing.push('BACKEND_API_URL');
  }
  
  if (!process.env.INTERNAL_API_KEY) {
    missing.push('INTERNAL_API_KEY');
  }
  
  return {
    valid: missing.length === 0,
    missing,
  };
}
