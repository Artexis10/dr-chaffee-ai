/**
 * Edge Runtime JWT Utilities
 * 
 * Provides JWT verification compatible with Next.js Edge Runtime (middleware).
 * Uses Web Crypto API instead of Node.js crypto module.
 * 
 * Security:
 * - Explicitly enforces HS256 algorithm
 * - Validates expiration
 * - Validates token type claim
 * - Timing-safe signature comparison
 */

// JWT algorithm - must match backend
const JWT_ALGORITHM = 'HS256';

/**
 * Get the session secret from environment.
 */
function getSecret(): string {
  // Check new env var first, then legacy
  const secret = process.env.AUTH_SESSION_SECRET || process.env.APP_SESSION_SECRET || '';
  
  if (!secret) {
    if (process.env.NODE_ENV === 'production') {
      throw new Error('AUTH_SESSION_SECRET must be set in production');
    }
    // Dev fallback - must match backend
    return 'dev-only-jwt-secret-do-not-use-in-production-min32chars';
  }
  
  return secret;
}

/**
 * Base64url decode a string
 */
function base64urlDecode(str: string): Uint8Array {
  // Add padding if needed
  const padded = str + '==='.slice(0, (4 - (str.length % 4)) % 4);
  // Convert base64url to base64
  const base64 = padded.replace(/-/g, '+').replace(/_/g, '/');
  // Decode
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes;
}

/**
 * Timing-safe comparison of two Uint8Arrays
 */
function timingSafeEqual(a: Uint8Array, b: Uint8Array): boolean {
  if (a.length !== b.length) {
    return false;
  }
  let result = 0;
  for (let i = 0; i < a.length; i++) {
    result |= a[i] ^ b[i];
  }
  return result === 0;
}

/**
 * JWT payload interface
 */
export interface JwtPayload {
  sub: string;      // User ID
  type: string;     // Token type ("access" or "refresh")
  iat: number;      // Issued at
  exp: number;      // Expiration
  discord_id?: string;
  tier?: string;
  username?: string;
}

/**
 * Verify a JWT access token.
 * 
 * @param token - The JWT string to verify
 * @returns Decoded payload if valid, null otherwise
 * 
 * Security:
 * - Explicitly enforces HS256 algorithm
 * - Validates expiration
 * - Validates token type is "access"
 */
export async function verifyAccessToken(token: string): Promise<JwtPayload | null> {
  if (!token || typeof token !== 'string') {
    return null;
  }
  
  const parts = token.split('.');
  if (parts.length !== 3) {
    return null;
  }
  
  const [headerB64, payloadB64, signatureB64] = parts;
  
  try {
    // Decode and validate header
    const headerJson = new TextDecoder().decode(base64urlDecode(headerB64));
    const header = JSON.parse(headerJson);
    
    // Explicitly enforce HS256 algorithm
    if (header.alg !== 'HS256') {
      console.warn('[JWT] Invalid algorithm:', header.alg);
      return null;
    }
    
    // Verify signature using Web Crypto API
    const secret = getSecret();
    const encoder = new TextEncoder();
    const key = await crypto.subtle.importKey(
      'raw',
      encoder.encode(secret),
      { name: 'HMAC', hash: 'SHA-256' },
      false,
      ['sign']
    );
    
    const signatureInput = encoder.encode(`${headerB64}.${payloadB64}`);
    const expectedSignature = new Uint8Array(
      await crypto.subtle.sign('HMAC', key, signatureInput)
    );
    
    const providedSignature = base64urlDecode(signatureB64);
    
    if (!timingSafeEqual(expectedSignature, providedSignature)) {
      return null;
    }
    
    // Decode payload
    const payloadJson = new TextDecoder().decode(base64urlDecode(payloadB64));
    const payload: JwtPayload = JSON.parse(payloadJson);
    
    // Validate token type
    if (payload.type !== 'access') {
      console.warn('[JWT] Invalid token type:', payload.type);
      return null;
    }
    
    // Check expiration
    const now = Math.floor(Date.now() / 1000);
    if (payload.exp < now) {
      return null; // Token expired
    }
    
    return payload;
    
  } catch (e) {
    // Any parsing or crypto error means invalid token
    return null;
  }
}

/**
 * Check if a token exists and appears to be a JWT (has 3 parts).
 * Does NOT validate the token - use verifyAccessToken for that.
 */
export function hasAccessToken(token: string | undefined): boolean {
  if (!token) return false;
  return token.split('.').length === 3;
}
