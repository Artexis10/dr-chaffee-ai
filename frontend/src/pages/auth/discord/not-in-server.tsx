import { useEffect, useState } from 'react';
import Head from 'next/head';
import Image from 'next/image';
import Link from 'next/link';

// Theme constants - must match DarkModeToggle.tsx
const THEME_KEY = 'askdrchaffee.theme';

export default function NotInServer() {
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
    infoBox: {
      background: isDarkMode ? '#1a1a2e' : '#eff6ff',
      padding: '1.25rem',
      borderRadius: '12px',
      marginBottom: '1.5rem',
      border: `1px solid ${isDarkMode ? '#2a2a4a' : '#bfdbfe'}`,
    },
    infoText: {
      color: isDarkMode ? '#a0a0c0' : '#1e40af',
      fontSize: '0.9rem',
      margin: 0,
      lineHeight: 1.6,
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
      background: '#5865F2',
      border: 'none',
      borderRadius: '12px',
      cursor: 'pointer',
      textDecoration: 'none',
      transition: 'all 0.2s',
      boxShadow: '0 4px 12px rgba(88, 101, 242, 0.3)',
      marginBottom: '1rem',
    },
    buttonSecondary: {
      display: 'inline-block',
      padding: '0.75rem 1.5rem',
      fontSize: '0.9rem',
      fontWeight: 500,
      color: isDarkMode ? '#f5f5f5' : '#374151',
      background: isDarkMode ? '#222222' : '#f3f4f6',
      border: `1px solid ${isDarkMode ? '#454545' : '#d1d5db'}`,
      borderRadius: '10px',
      textDecoration: 'none',
      cursor: 'pointer',
      transition: 'all 0.2s',
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
        <title>Not in Server - Ask Dr Chaffee</title>
        <meta name="description" content="You need to join the Discord server to access this application." />
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
              <line x1="15" y1="9" x2="9" y2="15"/>
              <line x1="9" y1="9" x2="15" y2="15"/>
            </svg>
          </div>

          <h1 style={styles.title}>Not a Server Member</h1>
          
          <p style={styles.subtitle}>
            You need to be a member of our Discord server to access Ask Dr Chaffee.
          </p>

          <div style={styles.infoBox}>
            <p style={styles.infoText}>
              💡 Join our Discord community to get access. Once you're a member with the appropriate role, 
              you'll be able to log in and explore Dr. Chaffee's knowledge base.
            </p>
          </div>

          {/* Placeholder for Discord invite link */}
          <a 
            href="#" 
            style={styles.buttonPrimary}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = '#4752C4';
              e.currentTarget.style.transform = 'translateY(-2px)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = '#5865F2';
              e.currentTarget.style.transform = 'translateY(0)';
            }}
          >
            <svg 
              width="20" 
              height="20" 
              viewBox="0 0 24 24" 
              fill="currentColor"
              style={{ marginRight: '0.5rem' }}
            >
              <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028 14.09 14.09 0 0 0 1.226-1.994.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z"/>
            </svg>
            Join Discord Server
          </a>

          <Link 
            href="/"
            style={styles.buttonSecondary}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = isDarkMode ? '#2d2d2d' : '#e5e7eb';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = isDarkMode ? '#222222' : '#f3f4f6';
            }}
          >
            Back to Login
          </Link>

          <div style={styles.footer}>
            <p style={styles.footerText}>
              Already a member? Try logging in again after joining the server.
            </p>
          </div>
        </div>
      </div>
    </>
  );
}
