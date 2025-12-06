import { NextRequest, NextResponse } from 'next/server';
import { verifySessionTokenEdge } from './src/utils/authTokenEdge';

/**
 * Next.js Middleware for authentication
 * 
 * Main App Protection:
 * - / (home) requires valid auth_token cookie
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
  
  const authTokenCookie = request.cookies.get('auth_token');
  const token = authTokenCookie?.value;
  
  if (!token) {
    // No token - redirect to login page
    return NextResponse.redirect(new URL('/login', request.url));
  }
  
  // Verify the signed token (checks signature and expiration)
  const payload = await verifySessionTokenEdge(token);
  
  if (!payload) {
    // Invalid or expired token - clear cookie and redirect to login
    const response = NextResponse.redirect(new URL('/login', request.url));
    response.cookies.delete('auth_token');
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
