import type { AppProps } from 'next/app';
import '../styles/globals.css';
import { PasswordGate } from '../components/PasswordGate';

export default function App({ Component, pageProps }: AppProps) {
  return (
    <PasswordGate>
      <Component {...pageProps} />
    </PasswordGate>
  );
}
