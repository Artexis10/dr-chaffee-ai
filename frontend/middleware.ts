import { NextRequest, NextResponse } from 'next/server';
import { verifySessionTokenEdge } from './src/utils/authTokenEdge';

/**
 * Next.js Middleware for authentication
 * 
 * Protects:
 * - /tuning/* routes (except /tuning/auth) - requires tuning_auth cookie
 * - Main app routes - requires valid signed auth_token cookie
 * 
 * Public routes:
 * - /api/* - API routes (protected at API level)
 * - /tuning/auth - Tuning login page
 * - /auth/discord/* - Discord OAuth flow pages (not-in-server, insufficient-role, error)
 * - / - Home page (shows PasswordGate component)
 */
export async function middleware(request: NextRequest) {
  const pathname = request.nextUrl.pathname;
  
  // Protect all /tuning routes EXCEPT /tuning/auth
  if (pathname.startsWith('/tuning') && pathname !== '/tuning/auth') {
    // Check if user has auth cookie
    const auth = request.cookies.get('tuning_auth');
    
    // If not authenticated, redirect to password page
    if (!auth) {
      return NextResponse.redirect(new URL('/tuning/auth', request.url));
    }
  }
  
  // Protect main app routes (all routes except /tuning/*, /tuning/auth, API routes, Discord auth, and home)
  // Allow access to: /, /api/*, /tuning/auth, /auth/discord/*
  const isApiRoute = pathname.startsWith('/api/');
  const isTuningAuth = pathname === '/tuning/auth';
  const isTuningRoute = pathname.startsWith('/tuning');
  const isHomePage = pathname === '/';
  const isDiscordAuthRoute = pathname.startsWith('/auth/discord');
  
  if (!isApiRoute && !isTuningAuth && !isTuningRoute && !isHomePage && !isDiscordAuthRoute) {
    // Check if user has main app auth token
    const authTokenCookie = request.cookies.get('auth_token');
    const token = authTokenCookie?.value;
    
    if (!token) {
      // No token - redirect to home (which shows password gate)
      return NextResponse.redirect(new URL('/', request.url));
    }
    
    // Verify the signed token (checks signature and expiration)
    const payload = await verifySessionTokenEdge(token);
    
    if (!payload) {
      // Invalid or expired token - clear cookie and redirect to home
      const response = NextResponse.redirect(new URL('/', request.url));
      response.cookies.delete('auth_token');
      return response;
    }
  }
  
  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    '/((?!_next/static|_next/image|favicon.ico).*)',
  ],
};
