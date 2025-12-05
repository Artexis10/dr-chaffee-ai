import { useState, useEffect, useRef } from 'react';
import Image from 'next/image';

interface PasswordGateProps {
  children: React.ReactNode;
}

// User info from Discord OAuth
interface DiscordUser {
  authenticated: boolean;
  id?: number;
  discord_id?: string;
  discord_username?: string;
  discord_global_name?: string;
  discord_avatar?: string;
  discord_tier?: string;
  discord_tier_label?: string;
  discord_tier_color?: string;
}

// Auth check timeout - if auth check takes longer than this, show login form
// This prevents infinite loading if backend is unreachable
const AUTH_CHECK_TIMEOUT_MS = 5000;

// Prefix for all console logs from this component
const LOG_PREFIX = '[PasswordGate]';

// Discord icon SVG component
function DiscordIcon() {
  return (
    <svg 
      width="20" 
      height="20" 
      viewBox="0 0 24 24" 
      fill="currentColor"
      style={{ marginRight: '0.5rem' }}
    >
      <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0 12.64 12.64 0 0 0-.617-1.25.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057 19.9 19.9 0 0 0 5.993 3.03.078.078 0 0 0 .084-.028 14.09 14.09 0 0 0 1.226-1.994.076.076 0 0 0-.041-.106 13.107 13.107 0 0 1-1.872-.892.077.077 0 0 1-.008-.128 10.2 10.2 0 0 0 .372-.292.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127 12.299 12.299 0 0 1-1.873.892.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028 19.839 19.839 0 0 0 6.002-3.03.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.956-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419 0-1.333.955-2.419 2.157-2.419 1.21 0 2.176 1.096 2.157 2.42 0 1.333-.946 2.418-2.157 2.418z"/>
    </svg>
  );
}

export function PasswordGate({ children }: PasswordGateProps) {
  const [password, setPassword] = useState('');
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [requiresPassword, setRequiresPassword] = useState(false);
  const [discordEnabled, setDiscordEnabled] = useState(false);
  const [discordError, setDiscordError] = useState('');
  const [discordUser, setDiscordUser] = useState<DiscordUser | null>(null);
  const [authCheckFailed, setAuthCheckFailed] = useState(false);
  const [authCheckMessage, setAuthCheckMessage] = useState<string | null>(null);
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const hasStartedAuthCheck = useRef(false);

  useEffect(() => {
    // Prevent double-execution in React StrictMode
    if (hasStartedAuthCheck.current) {
      console.info(LOG_PREFIX, 'Auth check already started, skipping duplicate');
      return;
    }
    hasStartedAuthCheck.current = true;
    
    console.info(LOG_PREFIX, 'Component mounted, starting auth check');
    
    // Simple async function with try/catch/finally
    const performAuthCheck = async () => {
      // Safety timeout: if auth check takes too long, show login form
      timeoutRef.current = setTimeout(() => {
        console.warn(LOG_PREFIX, `Auth check timed out after ${AUTH_CHECK_TIMEOUT_MS}ms - showing login form`);
        setIsLoading(false);
        setRequiresPassword(true);
        setAuthCheckFailed(true);
        setAuthCheckMessage('Auth check timed out. Please log in.');
      }, AUTH_CHECK_TIMEOUT_MS);

      try {
        console.info(LOG_PREFIX, 'Fetching /api/auth/check with credentials...');
        
        // Single fetch call with credentials: 'include' to send cookies
        const response = await fetch('/api/auth/check', {
          method: 'GET',
          credentials: 'include',
        });
        
        console.info(LOG_PREFIX, '/api/auth/check response status:', response.status);
        
        if (!response.ok) {
          throw new Error(`Auth check returned HTTP ${response.status}`);
        }
        
        const data = await response.json();
        console.info(LOG_PREFIX, 'Auth check response data:', data);
        
        // Clear timeout since we got a valid response
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current);
          timeoutRef.current = null;
        }
        
        // Simple decision: requiresPassword true or false
        if (data.requiresPassword === false) {
          console.info(LOG_PREFIX, 'requiresPassword=false - rendering children');
          setRequiresPassword(false);
        } else {
          // requiresPassword === true OR any unexpected value
          console.info(LOG_PREFIX, 'requiresPassword=true - showing login form');
          setRequiresPassword(true);
        }
        
        // Fetch Discord status in background (non-blocking)
        fetch('/api/auth/discord/status', { credentials: 'include' })
          .then(res => res.ok ? res.json() : { enabled: false })
          .then(d => setDiscordEnabled(d?.enabled === true))
          .catch(() => setDiscordEnabled(false));
        
      } catch (err) {
        console.error(LOG_PREFIX, 'Auth check failed:', err);
        // Clear timeout if still pending
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current);
          timeoutRef.current = null;
        }
        // On ANY error, show login form with message
        setRequiresPassword(true);
        setAuthCheckFailed(true);
        setAuthCheckMessage('Auth check failed. Please enter the app password to continue.');
      } finally {
        // CRITICAL: Always set isLoading=false, no matter what
        console.info(LOG_PREFIX, 'Auth check complete (finally), setting isLoading=false');
        setIsLoading(false);
      }
    };

    performAuthCheck();
    
    // Cleanup timeout on unmount
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, []);

  // Fetch Discord user info after successful login
  const fetchDiscordUser = async () => {
    try {
      const response = await fetch('/api/auth/discord/me', { credentials: 'include' });
      if (response.ok) {
        const data = await response.json();
        if (data.authenticated) {
          setDiscordUser(data);
        }
      }
    } catch (err) {
      console.debug(LOG_PREFIX, 'Could not fetch Discord user info:', err);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ password }),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        console.info(LOG_PREFIX, 'Login successful, rendering children');
        setIsAuthenticated(true);
        fetchDiscordUser();
      } else {
        setError(data.error || 'Invalid password. Please try again.');
        setPassword('');
      }
    } catch (err) {
      console.error(LOG_PREFIX, 'Login request failed:', err);
      setError('Authentication failed. Please try again.');
    }
  };

  // RENDER: Loading state - show a visible loading indicator
  if (isLoading) {
    console.info(LOG_PREFIX, 'Render: showing loading state');
    return (
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
        background: '#0a0a0a'
      }}>
        <div style={{ 
          color: '#ffffff', 
          fontSize: '1.25rem', 
          fontWeight: 600,
          marginBottom: '1rem'
        }}>
          Loading...
        </div>
        <div style={{ 
          color: '#888888', 
          fontSize: '0.875rem'
        }}>
          Checking authentication
        </div>
      </div>
    );
  }

  // RENDER: If no password required or already authenticated, show content
  if (!requiresPassword || isAuthenticated) {
    console.info(LOG_PREFIX, 'Render: showing children (authenticated or no password required)');
    return (
      <>
        {/* Tier badge overlay - only shown for Discord users with a tier */}
        {discordUser?.discord_tier_label && (
          <div style={{
            position: 'fixed',
            top: '1rem',
            right: '1rem',
            zIndex: 1000,
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            background: 'rgba(20, 20, 20, 0.95)',
            padding: '0.5rem 1rem',
            borderRadius: '8px',
            border: '1px solid #2d2d2d',
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)',
          }}>
            <span
              style={{
                display: 'inline-block',
                padding: '2px 8px',
                borderRadius: '9999px',
                fontSize: '0.75rem',
                fontWeight: 600,
                backgroundColor: discordUser.discord_tier_color ?? '#444',
                color: '#ffffff',
              }}
            >
              {discordUser.discord_tier_label}
            </span>
          </div>
        )}
        {children}
      </>
    );
  }

  // RENDER: Show password gate / login form
  console.info(LOG_PREFIX, 'Render: showing login form');
  
  return (
    <div style={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 50%, #0a0a0a 100%)',
      padding: '1rem'
    }}>
      <div style={{
        background: '#141414',
        borderRadius: '20px',
        padding: '2.5rem 2rem',
        maxWidth: '420px',
        width: '100%',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.6), 0 2px 8px rgba(0, 0, 0, 0.4)',
        border: '1px solid #2a2a2a',
        textAlign: 'center'
      }}>
        {/* Auth check failure message */}
        {authCheckFailed && authCheckMessage && (
          <div style={{
            background: '#422006',
            color: '#fbbf24',
            padding: '0.75rem',
            borderRadius: '8px',
            marginBottom: '1rem',
            fontSize: '0.85rem',
            border: '1px solid #854d0e'
          }}>
            ⚠️ {authCheckMessage}
          </div>
        )}
        
        {/* Dr. Chaffee Photo */}
        <div style={{
          width: '120px',
          height: '120px',
          margin: '0 auto 1.5rem',
          borderRadius: '50%',
          overflow: 'hidden',
          border: '4px solid #000000',
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)'
        }}>
          <Image 
            src="/dr-chaffee.jpg" 
            alt="Dr Anthony Chaffee" 
            width={120} 
            height={120}
            style={{ objectFit: 'cover' }}
          />
        </div>

        <h1 style={{
          fontSize: '2.2rem',
          fontWeight: 700,
          color: '#ffffff',
          marginBottom: '0.5rem',
          letterSpacing: '-0.02em'
        }}>
          Ask Dr Chaffee
        </h1>

        <p style={{
          color: '#b0b0b0',
          marginBottom: '2rem',
          fontSize: '1rem'
        }}>
          Interactive Knowledge Base
        </p>

        <div style={{
          background: '#222222',
          padding: '1rem',
          borderRadius: '12px',
          marginBottom: '1.5rem',
          border: '1px solid #2d2d2d'
        }}>
          <p style={{
            color: '#a0a0a0',
            fontSize: '0.9rem',
            margin: 0,
            lineHeight: 1.5
          }}>
            🔐 Main Application Access - Enter your password to explore Dr. Chaffee's knowledge base.
          </p>
        </div>

        <form onSubmit={handleSubmit}>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Enter password"
            autoFocus
            style={{
              width: '100%',
              padding: '1rem',
              fontSize: '1rem',
              border: error ? '2px solid #ef4444' : '2px solid #e2e8f0',
              borderRadius: '12px',
              marginBottom: '1rem',
              outline: 'none',
              transition: 'border-color 0.2s',
              boxSizing: 'border-box',
              backgroundColor: 'white',
              color: '#333333'
            }}
            onFocus={(e) => {
              if (!error) e.target.style.borderColor = '#000000';
            }}
            onBlur={(e) => {
              if (!error) e.target.style.borderColor = '#e2e8f0';
            }}
          />

          {error && (
            <div style={{
              background: '#fee2e2',
              color: '#dc2626',
              padding: '0.75rem',
              borderRadius: '8px',
              marginBottom: '1rem',
              fontSize: '0.9rem'
            }}>
              {error}
            </div>
          )}

          <button
            type="submit"
            style={{
              width: '100%',
              padding: '1rem',
              fontSize: '1rem',
              fontWeight: 600,
              color: 'white',
              background: 'linear-gradient(180deg, #1a1a1a 0%, #000000 100%)',
              border: 'none',
              borderRadius: '12px',
              cursor: 'pointer',
              transition: 'transform 0.2s, box-shadow 0.2s',
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.transform = 'translateY(-2px)';
              e.currentTarget.style.boxShadow = '0 6px 20px rgba(0, 0, 0, 0.4)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.3)';
            }}
          >
            Access Application
          </button>
        </form>

        {/* Discord Login Section */}
        <div style={{
          marginTop: '1.5rem',
          paddingTop: '1.5rem',
          borderTop: '1px solid #2d2d2d'
        }}>
          {/* Discord error message */}
          {discordError && (
            <div style={{
              background: '#fee2e2',
              color: '#dc2626',
              padding: '0.75rem',
              borderRadius: '8px',
              marginBottom: '0.75rem',
              fontSize: '0.85rem'
            }}>
              {discordError}
            </div>
          )}
          
          {/* Discord Login Button - only shown when Discord OAuth is configured */}
          {discordEnabled ? (
            <>
              <p style={{
                color: '#909090',
                fontSize: '0.85rem',
                marginBottom: '0.75rem',
                fontWeight: 500
              }}>
                Or sign in with
              </p>
              <button
                onClick={() => {
                  setDiscordError('');
                  // Navigate to Discord login
                  window.location.href = '/api/auth/discord/login';
                }}
                style={{
                  width: '100%',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  padding: '0.875rem 1rem',
                  fontSize: '1rem',
                  fontWeight: 600,
                  color: 'white',
                  background: '#5865F2',
                  border: 'none',
                  borderRadius: '12px',
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  boxShadow: '0 4px 12px rgba(88, 101, 242, 0.3)'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = '#4752C4';
                  e.currentTarget.style.transform = 'translateY(-2px)';
                  e.currentTarget.style.boxShadow = '0 6px 20px rgba(88, 101, 242, 0.4)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = '#5865F2';
                  e.currentTarget.style.transform = 'translateY(0)';
                  e.currentTarget.style.boxShadow = '0 4px 12px rgba(88, 101, 242, 0.3)';
                }}
              >
                <DiscordIcon />
                Log in with Discord
              </button>
            </>
          ) : (
            <p style={{
              color: '#707070',
              fontSize: '0.8rem',
              textAlign: 'center',
              margin: 0
            }}>
              Discord login isn't available yet. Please use the access password to sign in.
            </p>
          )}
        </div>

        <div style={{
          marginTop: '1.5rem',
          paddingTop: '1.5rem',
          borderTop: '1px solid #2d2d2d'
        }}>
          <p style={{
            color: '#909090',
            fontSize: '0.85rem',
            marginBottom: '0.75rem',
            fontWeight: 500
          }}>
            Need admin access?
          </p>
          <a
            href="/tuning/auth"
            style={{
              display: 'inline-block',
              padding: '0.625rem 1.25rem',
              fontSize: '0.875rem',
              fontWeight: 500,
              color: '#f5f5f5',
              background: '#222222',
              border: '1px solid #454545',
              borderRadius: '10px',
              textDecoration: 'none',
              cursor: 'pointer',
              transition: 'all 0.2s'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = '#2d2d2d';
              e.currentTarget.style.borderColor = '#606060';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = '#222222';
              e.currentTarget.style.borderColor = '#454545';
            }}
          >
            Tuning Dashboard
          </a>
        </div>

        <p style={{
          marginTop: '2rem',
          color: '#94a3b8',
          fontSize: '0.85rem'
        }}>
          Based on Dr Anthony Chaffee's content
        </p>
      </div>
    </div>
  );
}
