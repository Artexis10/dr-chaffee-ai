'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/router';
import Image from 'next/image';
import Head from 'next/head';

/**
 * Dedicated Login Page for Main App
 * 
 * This page handles:
 * - Password authentication
 * - Discord OAuth login
 * - Redirect to / after successful login
 * 
 * Middleware redirects unauthenticated users here from protected routes.
 */

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

// Skeleton loading state for the login card
function LoginSkeleton() {
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
        {/* Avatar skeleton */}
        <div style={{
          width: '120px',
          height: '120px',
          margin: '0 auto 1.5rem',
          borderRadius: '50%',
          background: 'linear-gradient(90deg, #2a2a2a 25%, #3a3a3a 50%, #2a2a2a 75%)',
          backgroundSize: '200% 100%',
          animation: 'shimmer 1.5s infinite',
        }} />
        
        {/* Title skeleton */}
        <div style={{
          height: '2.2rem',
          width: '70%',
          margin: '0 auto 0.5rem',
          borderRadius: '8px',
          background: 'linear-gradient(90deg, #2a2a2a 25%, #3a3a3a 50%, #2a2a2a 75%)',
          backgroundSize: '200% 100%',
          animation: 'shimmer 1.5s infinite',
        }} />
        
        {/* Subtitle skeleton */}
        <div style={{
          height: '1rem',
          width: '50%',
          margin: '0 auto 2rem',
          borderRadius: '6px',
          background: 'linear-gradient(90deg, #2a2a2a 25%, #3a3a3a 50%, #2a2a2a 75%)',
          backgroundSize: '200% 100%',
          animation: 'shimmer 1.5s infinite',
        }} />
        
        {/* Input skeleton */}
        <div style={{
          height: '3rem',
          width: '100%',
          marginBottom: '1rem',
          borderRadius: '12px',
          background: 'linear-gradient(90deg, #2a2a2a 25%, #3a3a3a 50%, #2a2a2a 75%)',
          backgroundSize: '200% 100%',
          animation: 'shimmer 1.5s infinite',
        }} />
        
        {/* Button skeleton */}
        <div style={{
          height: '3rem',
          width: '100%',
          borderRadius: '12px',
          background: 'linear-gradient(90deg, #2a2a2a 25%, #3a3a3a 50%, #2a2a2a 75%)',
          backgroundSize: '200% 100%',
          animation: 'shimmer 1.5s infinite',
        }} />
        
        <style jsx>{`
          @keyframes shimmer {
            0% { background-position: -200% 0; }
            100% { background-position: 200% 0; }
          }
        `}</style>
      </div>
    </div>
  );
}

export default function LoginPage() {
  const router = useRouter();
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [discordEnabled, setDiscordEnabled] = useState(false);
  const [discordLoading, setDiscordLoading] = useState(false);
  const hasCheckedAuth = useRef(false);

  // Check if user is already authenticated
  useEffect(() => {
    if (hasCheckedAuth.current) return;
    hasCheckedAuth.current = true;

    const checkAuth = async () => {
      try {
        const response = await fetch('/api/auth/check', {
          method: 'GET',
          credentials: 'include',
        });
        
        if (response.ok) {
          const data = await response.json();
          
          // If user is already authenticated, redirect to home
          if (data.requiresPassword === false) {
            router.replace('/');
            return;
          }
        }
        
        // Fetch Discord status
        fetch('/api/auth/discord/status', { credentials: 'include' })
          .then(res => res.ok ? res.json() : { enabled: false })
          .then(d => setDiscordEnabled(d?.enabled === true))
          .catch(() => setDiscordEnabled(false));
          
      } catch (err) {
        console.error('[Login] Auth check failed:', err);
      } finally {
        setIsLoading(false);
      }
    };

    checkAuth();
  }, [router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsSubmitting(true);

    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ password }),
      });

      const data = await response.json();

      if (response.ok && data.success) {
        // Redirect to home page
        router.replace('/');
      } else {
        setError(data.error || 'Invalid password. Please try again.');
        setPassword('');
      }
    } catch (err) {
      console.error('[Login] Login request failed:', err);
      setError('Authentication failed. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDiscordLogin = () => {
    setDiscordLoading(true);
    window.location.href = '/api/auth/discord/login';
  };

  // Show skeleton while checking auth
  if (isLoading) {
    return (
      <>
        <Head>
          <title>Login | Ask Dr Chaffee</title>
        </Head>
        <LoginSkeleton />
      </>
    );
  }

  return (
    <>
      <Head>
        <title>Login | Ask Dr Chaffee</title>
        <meta name="description" content="Login to Ask Dr Chaffee - Interactive Knowledge Base" />
      </Head>
      
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
              priority
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
              🔐 Enter your password to access the knowledge base.
            </p>
          </div>

          <form onSubmit={handleSubmit}>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter password"
              autoFocus
              disabled={isSubmitting}
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
                color: '#333333',
                opacity: isSubmitting ? 0.7 : 1,
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
              disabled={isSubmitting}
              style={{
                width: '100%',
                padding: '1rem',
                fontSize: '1rem',
                fontWeight: 600,
                color: 'white',
                background: isSubmitting 
                  ? '#333333' 
                  : 'linear-gradient(180deg, #1a1a1a 0%, #000000 100%)',
                border: 'none',
                borderRadius: '12px',
                cursor: isSubmitting ? 'not-allowed' : 'pointer',
                transition: 'transform 0.2s, box-shadow 0.2s',
                boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)'
              }}
            >
              {isSubmitting ? 'Signing in...' : 'Access Application'}
            </button>
          </form>

          {/* Discord Login Section */}
          <div style={{
            marginTop: '1.5rem',
            paddingTop: '1.5rem',
            borderTop: '1px solid #2d2d2d'
          }}>
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
                  onClick={handleDiscordLogin}
                  disabled={discordLoading}
                  style={{
                    width: '100%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    padding: '0.875rem 1rem',
                    fontSize: '1rem',
                    fontWeight: 600,
                    color: 'white',
                    background: discordLoading ? '#4752C4' : '#5865F2',
                    border: 'none',
                    borderRadius: '12px',
                    cursor: discordLoading ? 'not-allowed' : 'pointer',
                    transition: 'all 0.2s',
                    boxShadow: '0 4px 12px rgba(88, 101, 242, 0.3)',
                    opacity: discordLoading ? 0.8 : 1,
                  }}
                >
                  <DiscordIcon />
                  {discordLoading ? 'Redirecting to Discord...' : 'Log in with Discord'}
                </button>
              </>
            ) : (
              <p style={{
                color: '#707070',
                fontSize: '0.8rem',
                textAlign: 'center',
                margin: 0
              }}>
                Discord login is not available. Please use the password to sign in.
              </p>
            )}
          </div>

          {/* Tuning Dashboard Link */}
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
            >
              Tuning Dashboard
            </a>
          </div>

          <p style={{
            marginTop: '2rem',
            color: '#94a3b8',
            fontSize: '0.85rem'
          }}>
            Based on Dr Anthony Chaffee&apos;s content
          </p>
        </div>
      </div>
    </>
  );
}

// Bypass PasswordGate for this page - it IS the login page
LoginPage.getLayout = (page: React.ReactElement) => page;
