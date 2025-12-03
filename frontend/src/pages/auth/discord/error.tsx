import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import Head from 'next/head';
import Link from 'next/link';

// Theme constants - must match DarkModeToggle.tsx
const THEME_KEY = 'askdrchaffee.theme';

export default function DiscordError() {
  const router = useRouter();
  const { error } = router.query;
  const [isDarkMode, setIsDarkMode] = useState(true);

  // Initialize theme on mount (default to DARK)
  useEffect(() => {
    const storedTheme = localStorage.getItem(THEME_KEY);
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    let shouldBeDark: boolean;
    if (storedTheme === 'dark') {
      shouldBeDark = true;
    } else if (storedTheme === 'light') {
      shouldBeDark = false;
    } else {
      shouldBeDark = prefersDark !== false;
    }
    
    setIsDarkMode(shouldBeDark);
    
    const root = document.documentElement;
    if (shouldBeDark) {
      root.classList.add('dark-mode');
      root.classList.remove('light-mode');
    } else {
      root.classList.remove('dark-mode');
      root.classList.add('light-mode');
    }
  }, []);

  // Map error codes to user-friendly messages
  const getErrorMessage = (errorCode: string | string[] | undefined): string => {
    const code = Array.isArray(errorCode) ? errorCode[0] : errorCode;
    
    switch (code) {
      case 'access_denied':
        return 'You cancelled the Discord authorization.';
      case 'invalid_state':
        return 'Security validation failed. Please try again.';
      case 'token_exchange_failed':
        return 'Failed to complete authentication with Discord.';
      case 'user_fetch_failed':
        return 'Could not retrieve your Discord profile.';
      case 'database_error':
        return 'A database error occurred. Please try again later.';
      case 'token_creation_failed':
        return 'Failed to create your session. Please try again.';
      case 'missing_params':
        return 'Invalid callback parameters. Please try again.';
      default:
        return 'An unexpected error occurred during Discord login.';
    }
  };

  const styles = {
    container: {
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      minHeight: '100vh',
      background: isDarkMode 
        ? 'linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 50%, #0a0a0a 100%)'
        : 'linear-gradient(135deg, #f5f5f5 0%, #ffffff 50%, #f5f5f5 100%)',
      padding: '1rem',
    },
    card: {
      background: isDarkMode ? '#141414' : '#ffffff',
      borderRadius: '20px',
      padding: '2.5rem 2rem',
      maxWidth: '480px',
      width: '100%',
      boxShadow: isDarkMode 
        ? '0 8px 32px rgba(0, 0, 0, 0.6), 0 2px 8px rgba(0, 0, 0, 0.4)'
        : '0 8px 32px rgba(0, 0, 0, 0.1), 0 2px 8px rgba(0, 0, 0, 0.05)',
      border: `1px solid ${isDarkMode ? '#2a2a2a' : '#e5e5e5'}`,
      textAlign: 'center' as const,
    },
    iconContainer: {
      width: '80px',
      height: '80px',
      margin: '0 auto 1.5rem',
      borderRadius: '50%',
      background: isDarkMode ? '#2a1a1a' : '#fef2f2',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      border: `2px solid ${isDarkMode ? '#4a2a2a' : '#fecaca'}`,
    },
    title: {
      fontSize: '1.75rem',
      fontWeight: 700,
      color: isDarkMode ? '#ffffff' : '#1a1a1a',
      marginBottom: '0.75rem',
      letterSpacing: '-0.02em',
    },
    subtitle: {
      color: isDarkMode ? '#b0b0b0' : '#6b7280',
      marginBottom: '1.5rem',
      fontSize: '1rem',
      lineHeight: 1.6,
    },
    errorCode: {
      background: isDarkMode ? '#1a1a1a' : '#f3f4f6',
      padding: '0.5rem 1rem',
      borderRadius: '8px',
      marginBottom: '1.5rem',
      fontFamily: 'monospace',
      fontSize: '0.85rem',
      color: isDarkMode ? '#a0a0a0' : '#6b7280',
    },
    buttonPrimary: {
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      width: '100%',
      padding: '1rem',
      fontSize: '1rem',
      fontWeight: 600,
      color: 'white',
      background: isDarkMode 
        ? 'linear-gradient(180deg, #1a1a1a 0%, #000000 100%)'
        : 'linear-gradient(180deg, #374151 0%, #1f2937 100%)',
      border: 'none',
      borderRadius: '12px',
      cursor: 'pointer',
      textDecoration: 'none',
      transition: 'all 0.2s',
      boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)',
    },
    footer: {
      marginTop: '2rem',
      paddingTop: '1.5rem',
      borderTop: `1px solid ${isDarkMode ? '#2d2d2d' : '#e5e5e5'}`,
    },
    footerText: {
      color: isDarkMode ? '#94a3b8' : '#6b7280',
      fontSize: '0.85rem',
    },
  };

  return (
    <>
      <Head>
        <title>Login Error - Ask Dr Chaffee</title>
        <meta name="description" content="An error occurred during Discord login." />
      </Head>

      <div style={styles.container}>
        <div style={styles.card}>
          {/* Error Icon */}
          <div style={styles.iconContainer}>
            <svg 
              width="40" 
              height="40" 
              viewBox="0 0 24 24" 
              fill="none" 
              stroke={isDarkMode ? '#ef4444' : '#dc2626'}
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <circle cx="12" cy="12" r="10"/>
              <line x1="12" y1="8" x2="12" y2="12"/>
              <line x1="12" y1="16" x2="12.01" y2="16"/>
            </svg>
          </div>

          <h1 style={styles.title}>Login Failed</h1>
          
          <p style={styles.subtitle}>
            {getErrorMessage(error)}
          </p>

          {error && (
            <div style={styles.errorCode}>
              Error code: {error}
            </div>
          )}

          <Link 
            href="/"
            style={styles.buttonPrimary}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'translateY(-2px)';
              e.currentTarget.style.boxShadow = '0 6px 20px rgba(0, 0, 0, 0.4)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.3)';
            }}
          >
            Try Again
          </Link>

          <div style={styles.footer}>
            <p style={styles.footerText}>
              If this problem persists, please contact support.
            </p>
          </div>
        </div>
      </div>
    </>
  );
}
