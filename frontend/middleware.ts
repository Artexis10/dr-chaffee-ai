import { NextRequest, NextResponse } from 'next/server';

export function middleware(request: NextRequest) {
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
  
  // Protect main app routes (all routes except /tuning/*, /tuning/auth, and API routes)
  // Allow access to: /, /api/*, /tuning/auth
  const isApiRoute = pathname.startsWith('/api/');
  const isTuningAuth = pathname === '/tuning/auth';
  const isTuningRoute = pathname.startsWith('/tuning');
  
  if (!isApiRoute && !isTuningAuth && !isTuningRoute) {
    // Check if user has main app auth token
    const authToken = request.cookies.get('auth_token');
    
    // If not authenticated, redirect to home (which shows password gate)
    if (!authToken) {
      return NextResponse.redirect(new URL('/', request.url));
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
