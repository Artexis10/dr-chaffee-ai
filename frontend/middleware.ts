import { NextRequest, NextResponse } from 'next/server';
import { verifyAccessToken, hasAccessToken } from './src/utils/jwtEdge';

/**
 * Next.js Middleware for authentication
 * 
 * Main App Protection:
 * - / (home) requires valid access_token cookie (JWT)
 * - Unauthenticated users are redirected to /login
 * - /login is public (the login page itself)
 * 
 * Tuning Dashboard Protection:
 * - /tuning/* routes (except /tuning/auth) require tuning_auth cookie
 * - /tuning/auth is public (tuning login page)
 * 
 * Public Routes (no auth required):
 * - /login - Main app login page
 * - /api/* - API routes (protected at API level)
 * - /tuning/auth - Tuning login page
 * - /auth/discord/* - Discord OAuth flow pages (error, not-in-server, insufficient-role)
 * - Static assets (/_next/*, favicon.ico, etc.)
 * 
 * Token Strategy:
 * - access_token: Short-lived JWT (8h), HttpOnly cookie
 * - refresh_token: Long-lived JWT (30d), HttpOnly cookie
 * - Middleware only checks access_token; refresh happens via /api/auth/me
 */
export async function middleware(request: NextRequest) {
  const pathname = request.nextUrl.pathname;
  
  // ============================================
  // PUBLIC ROUTES - No auth required
  // ============================================
  
  // Login page is always public
  if (pathname === '/login') {
    return NextResponse.next();
  }
  
  // API routes are protected at the API level, not middleware
  if (pathname.startsWith('/api/')) {
    return NextResponse.next();
  }
  
  // Discord OAuth error/status pages are public
  if (pathname.startsWith('/auth/discord')) {
    return NextResponse.next();
  }
  
  // Tuning auth page is public
  if (pathname === '/tuning/auth') {
    return NextResponse.next();
  }
  
  // ============================================
  // TUNING DASHBOARD PROTECTION
  // ============================================
  
  if (pathname.startsWith('/tuning')) {
    const tuningAuth = request.cookies.get('tuning_auth');
    
    if (!tuningAuth) {
      return NextResponse.redirect(new URL('/tuning/auth', request.url));
    }
    
    // Tuning auth is valid, allow access
    return NextResponse.next();
  }
  
  // ============================================
  // MAIN APP PROTECTION (/, and any other routes)
  // ============================================
  
  // Try new JWT access_token first
  const accessTokenCookie = request.cookies.get('access_token');
  const accessToken = accessTokenCookie?.value;
  
  // Check if we have a refresh token (for potential refresh via /api/auth/me)
  const refreshTokenCookie = request.cookies.get('refresh_token');
  const hasRefreshToken = !!refreshTokenCookie?.value && hasAccessToken(refreshTokenCookie.value);
  
  if (!accessToken) {
    // No access token - check if we have refresh token
    // If we have refresh token, allow through so /api/auth/me can refresh
    // The page will call /api/auth/me which handles the refresh
    if (hasRefreshToken) {
      // Allow through - the page should call /api/auth/me to refresh
      return NextResponse.next();
    }
    
    // No tokens at all - redirect to login
    return NextResponse.redirect(new URL('/login', request.url));
  }
  
  // Verify the JWT access token
  const payload = await verifyAccessToken(accessToken);
  
  if (!payload) {
    // Access token invalid/expired - check for refresh token
    if (hasRefreshToken) {
      // Allow through - the page should call /api/auth/me to refresh
      return NextResponse.next();
    }
    
    // No valid tokens - clear cookies and redirect to login
    const response = NextResponse.redirect(new URL('/login', request.url));
    response.cookies.delete('access_token');
    response.cookies.delete('refresh_token');
    return response;
  }
  
  // Token is valid, allow access
  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - Public assets (images, etc.)
     */
    '/((?!_next/static|_next/image|favicon.ico|.*\\.(?:jpg|jpeg|png|gif|ico|svg|webp)$).*)',
  ],
};
