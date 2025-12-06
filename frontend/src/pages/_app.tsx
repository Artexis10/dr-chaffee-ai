import { useEffect, ReactElement, ReactNode } from 'react';
import type { AppProps } from 'next/app';
import type { NextPage } from 'next';
import '../styles/globals.css';
import { getSessionId } from '../utils/session';

/**
 * Custom page type that supports per-page layouts.
 * Pages can define getLayout to customize the default layout.
 * 
 * NOTE: Authentication is now handled by middleware.ts, not PasswordGate.
 * - Unauthenticated users are redirected to /login by middleware
 * - / and other protected routes assume user is authenticated
 */
export type NextPageWithLayout<P = object, IP = P> = NextPage<P, IP> & {
  getLayout?: (page: ReactElement) => ReactNode;
};

type AppPropsWithLayout = AppProps & {
  Component: NextPageWithLayout;
};

export default function App({ Component, pageProps }: AppPropsWithLayout) {
  // Dev-only: Log session ID once on app load for debugging
  useEffect(() => {
    if (process.env.NODE_ENV === 'development') {
      const sessionId = getSessionId();
      console.log(`🔍 Dr Chaffee AI session: ${sessionId}`);
    }
  }, []);

  // Use the page's custom layout if defined, otherwise render directly
  // Auth is handled by middleware - no need for PasswordGate wrapper
  const getLayout = Component.getLayout ?? ((page) => page);

  return getLayout(<Component {...pageProps} />);
}
