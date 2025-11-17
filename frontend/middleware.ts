import { NextRequest, NextResponse } from 'next/server';

export function middleware(request: NextRequest) {
  // Only protect the /tuning route
  if (request.nextUrl.pathname === '/tuning') {
    // Check if user has auth cookie
    const auth = request.cookies.get('tuning_auth');
    
    // If not authenticated, redirect to password page
    if (!auth) {
      return NextResponse.redirect(new URL('/tuning/auth', request.url));
    }
  }
  
  return NextResponse.next();
}

export const config = {
  matcher: ['/tuning/:path*'],
};
