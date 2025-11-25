/**
 * Edge Runtime compatible token verification
 * 
 * This is a lightweight version of authToken.ts that works in Next.js Edge Runtime
 * (middleware). It uses the Web Crypto API instead of Node's crypto module.
 * 
 * Required env var: APP_SESSION_SECRET (must be set in production)
 */

/**
 * Get the session secret from environment.
 * In production, this MUST be set. In dev, falls back to a dev-only secret.
 */
function getSessionSecret(): string {
  const secret = process.env.APP_SESSION_SECRET;
  
  if (!secret || secret.trim().length === 0) {
    // In production, require the secret to be set
    if (process.env.NODE_ENV === 'production') {
      console.error('[Auth] APP_SESSION_SECRET must be set in production');
      return '';  // Will cause verification to fail
    }
    // In development, use a fallback (clearly marked as dev-only)
    return 'dev-only-secret-do-not-use-in-production';
  }
  
  return secret;
}

/**
 * Base64url decode a string
 */
function base64urlDecode(str: string): string {
  // Add back padding if needed
  const padded = str + '==='.slice(0, (4 - (str.length % 4)) % 4);
  const base64 = padded.replace(/-/g, '+').replace(/_/g, '/');
  
  // Use atob for Edge Runtime compatibility
  try {
    return atob(base64);
  } catch {
    return '';
  }
}

/**
 * Create an HMAC-SHA256 signature using Web Crypto API
 */
async function createSignatureAsync(payload: string, secret: string): Promise<string> {
  const encoder = new TextEncoder();
  const keyData = encoder.encode(secret);
  const messageData = encoder.encode(payload);
  
  const key = await crypto.subtle.importKey(
    'raw',
    keyData,
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );
  
  const signature = await crypto.subtle.sign('HMAC', key, messageData);
  
  // Convert to base64url
  const bytes = new Uint8Array(signature);
  let binary = '';
  for (let i = 0; i < bytes.length; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  const base64 = btoa(binary);
  return base64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

/**
 * Timing-safe comparison of two strings
 */
function timingSafeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) {
    return false;
  }
  
  let result = 0;
  for (let i = 0; i < a.length; i++) {
    result |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return result === 0;
}

export interface TokenPayload {
  iat: number;  // Issued at (Unix timestamp)
  exp: number;  // Expiration (Unix timestamp)
}

/**
 * Verify a signed session token (async version for Edge Runtime).
 * Checks signature validity and expiration.
 * 
 * @param token - The token to verify
 * @returns The decoded payload if valid, null otherwise
 */
export async function verifySessionTokenEdge(token: string): Promise<TokenPayload | null> {
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
    if (!secret) {
      return null;
    }
    
    // Recompute signature and compare in timing-safe manner
    const expectedSignature = await createSignatureAsync(payloadStr, secret);
    if (!timingSafeEqual(providedSignature, expectedSignature)) {
      return null;
    }
    
    // Parse and validate payload
    const payloadJson = base64urlDecode(payloadStr);
    if (!payloadJson) {
      return null;
    }
    
    const payload: TokenPayload = JSON.parse(payloadJson);
    
    // Check expiration
    const now = Math.floor(Date.now() / 1000);
    if (payload.exp < now) {
      return null;  // Token expired
    }
    
    return payload;
  } catch {
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
export async function isValidTokenEdge(token: string): Promise<boolean> {
  return (await verifySessionTokenEdge(token)) !== null;
}
