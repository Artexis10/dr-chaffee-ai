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
  
  return NextResponse.next();
}

export const config = {
  matcher: ['/tuning/:path*'],
};
