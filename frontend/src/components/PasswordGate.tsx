import { useState, useEffect } from 'react';
import Image from 'next/image';
import { apiFetch } from '@/utils/api';

interface PasswordGateProps {
  children: React.ReactNode;
}

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

  useEffect(() => {
    // Check localStorage first (synchronous, no flash)
    const authToken = localStorage.getItem('auth_token');
    
    // Check if password is required and if Discord is enabled
    Promise.all([
      apiFetch('/api/auth/check').then(res => res.json()),
      apiFetch('/api/auth/discord/status').then(res => res.json()).catch(() => ({ enabled: false }))
    ])
      .then(([authData, discordData]) => {
        setRequiresPassword(authData.requiresPassword);
        setDiscordEnabled(discordData.enabled === true);
        
        // If already have token and password is required, verify it
        if (authToken && authData.requiresPassword) {
          // Verify token
          apiFetch('/api/auth/verify', {
            headers: { 'Authorization': `Bearer ${authToken}` }
          })
            .then(res => res.json())
            .then(result => {
              if (result.valid) {
                setIsAuthenticated(true);
              } else {
                localStorage.removeItem('auth_token');
              }
              setIsLoading(false);
            })
            .catch(() => {
              localStorage.removeItem('auth_token');
              setIsLoading(false);
            });
        } else {
          setIsLoading(false);
        }
      })
      .catch(() => {
        setIsLoading(false);
        setRequiresPassword(false);
      });
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    try {
      const response = await apiFetch('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({ password })
      });

      const data = await response.json();

      if (response.ok && data.token) {
        localStorage.setItem('auth_token', data.token);
        setIsAuthenticated(true);
      } else {
        setError('Invalid password. Please try again.');
        setPassword('');
      }
    } catch (err) {
      setError('Authentication failed. Please try again.');
    }
  };

  if (isLoading) {
    return (
      <div style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        minHeight: '100vh',
        background: '#050505'
      }}>
        <div style={{ color: '#a0a0a0', fontSize: '1rem', fontWeight: 500 }}>Loading...</div>
      </div>
    );
  }

  // If no password required or already authenticated, show content
  if (!requiresPassword || isAuthenticated) {
    return <>{children}</>;
  }

  // Show password gate
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

        {/* Discord Login Button - only shown when Discord OAuth is configured */}
        {discordEnabled && (
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
              Or sign in with
            </p>
            <button
              onClick={() => {
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
          </div>
        )}

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
