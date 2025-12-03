import { useEffect } from 'react';
import type { AppProps } from 'next/app';
import '../styles/globals.css';
import { PasswordGate } from '../components/PasswordGate';
import { getSessionId } from '../utils/session';

export default function App({ Component, pageProps }: AppProps) {
  // Dev-only: Log session ID once on app load for debugging
  useEffect(() => {
    if (process.env.NODE_ENV === 'development') {
      const sessionId = getSessionId();
      console.log(`🔍 Dr Chaffee AI session: ${sessionId}`);
    }
  }, []);

  return (
    <PasswordGate>
      <Component {...pageProps} />
    </PasswordGate>
  );
}
