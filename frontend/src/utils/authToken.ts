/**
 * Signed Session Token Utilities
 * 
 * Provides HMAC-SHA256 signed tokens for secure session management.
 * Tokens contain an expiration time and are validated cryptographically.
 * 
 * Required env var: APP_SESSION_SECRET (must be set in production)
 */

import * as crypto from 'crypto';

// Session token expiration (7 days in seconds)
const TOKEN_EXPIRY_SECONDS = 7 * 24 * 60 * 60;

/**
 * Get the session secret from environment.
 * In production, this MUST be set. In dev, falls back to a dev-only secret.
 */
function getSessionSecret(): string {
  const secret = process.env.APP_SESSION_SECRET;
  
  if (!secret || secret.trim().length === 0) {
    // In production, require the secret to be set
    if (process.env.NODE_ENV === 'production') {
      throw new Error('APP_SESSION_SECRET must be set in production');
    }
    // In development, use a fallback (clearly marked as dev-only)
    console.warn('[Auth] WARNING: Using dev-only session secret. Set APP_SESSION_SECRET in production.');
    return 'dev-only-secret-do-not-use-in-production';
  }
  
  return secret;
}

/**
 * Base64url encode a string (URL-safe base64)
 */
function base64urlEncode(str: string): string {
  return Buffer.from(str, 'utf8')
    .toString('base64')
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
}

/**
 * Base64url decode a string
 */
function base64urlDecode(str: string): string {
  // Add back padding if needed
  const padded = str + '==='.slice(0, (4 - (str.length % 4)) % 4);
  return Buffer.from(
    padded.replace(/-/g, '+').replace(/_/g, '/'),
    'base64'
  ).toString('utf8');
}

/**
 * Create an HMAC-SHA256 signature for a payload
 */
function createSignature(payload: string, secret: string): string {
  return crypto
    .createHmac('sha256', secret)
    .update(payload)
    .digest('base64')
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/, '');
}

/**
 * Timing-safe comparison of two strings
 */
function timingSafeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) {
    return false;
  }
  return crypto.timingSafeEqual(Buffer.from(a), Buffer.from(b));
}

export interface TokenPayload {
  iat: number;  // Issued at (Unix timestamp)
  exp: number;  // Expiration (Unix timestamp)
}

/**
 * Create a signed session token.
 * Token format: <base64url(payload)>.<base64url(signature)>
 * 
 * @returns Signed token string
 */
export function createSessionToken(): string {
  const secret = getSessionSecret();
  const now = Math.floor(Date.now() / 1000);
  
  const payload: TokenPayload = {
    iat: now,
    exp: now + TOKEN_EXPIRY_SECONDS,
  };
  
  const payloadStr = base64urlEncode(JSON.stringify(payload));
  const signature = createSignature(payloadStr, secret);
  
  return `${payloadStr}.${signature}`;
}

/**
 * Verify a signed session token.
 * Checks signature validity and expiration.
 * 
 * @param token - The token to verify
 * @returns The decoded payload if valid, null otherwise
 */
export function verifySessionToken(token: string): TokenPayload | null {
  if (!token || typeof token !== 'string') {
    return null;
  }
  
  const parts = token.split('.');
  if (parts.length !== 2) {
    return null;
  }
  
  const [payloadStr, providedSignature] = parts;
  
  try {
    const secret = getSessionSecret();
    
    // Recompute signature and compare in timing-safe manner
    const expectedSignature = createSignature(payloadStr, secret);
    if (!timingSafeEqual(providedSignature, expectedSignature)) {
      return null;
    }
    
    // Parse and validate payload
    const payload: TokenPayload = JSON.parse(base64urlDecode(payloadStr));
    
    // Check expiration
    const now = Math.floor(Date.now() / 1000);
    if (payload.exp < now) {
      return null;  // Token expired
    }
    
    return payload;
  } catch (e) {
    // Any parsing or crypto error means invalid token
    return null;
  }
}

/**
 * Check if a token is valid (convenience wrapper)
 * 
 * @param token - The token to check
 * @returns true if token is valid and not expired
 */
export function isValidToken(token: string): boolean {
  return verifySessionToken(token) !== null;
}
