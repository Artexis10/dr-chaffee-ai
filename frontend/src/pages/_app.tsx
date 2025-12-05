import { useEffect, ReactElement, ReactNode } from 'react';
import type { AppProps } from 'next/app';
import type { NextPage } from 'next';
import '../styles/globals.css';
import { PasswordGate } from '../components/PasswordGate';
import { getSessionId } from '../utils/session';

/**
 * Custom page type that supports per-page layouts.
 * Pages can define getLayout to bypass or customize the default layout.
 */
export type NextPageWithLayout<P = {}, IP = P> = NextPage<P, IP> & {
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

  // Use the page's custom layout if defined, otherwise use PasswordGate
  const getLayout = Component.getLayout ?? ((page) => (
    <PasswordGate>
      {page}
    </PasswordGate>
  ));

  return getLayout(<Component {...pageProps} />);
}
