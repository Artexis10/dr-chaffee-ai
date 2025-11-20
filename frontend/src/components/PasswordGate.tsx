import { useState, useEffect } from 'react';
import Image from 'next/image';

interface PasswordGateProps {
  children: React.ReactNode;
}

export function PasswordGate({ children }: PasswordGateProps) {
  const [password, setPassword] = useState('');
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [requiresPassword, setRequiresPassword] = useState(false);

  useEffect(() => {
    // Check localStorage first (synchronous, no flash)
    const authToken = localStorage.getItem('auth_token');
    
    // Check if password is required
    fetch('/api/auth/check')
      .then(res => res.json())
      .then(data => {
        setRequiresPassword(data.requiresPassword);
        
        // If already have token and password is required, verify it
        if (authToken && data.requiresPassword) {
          // Verify token
          fetch('/api/auth/verify', {
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
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
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
        background: '#0a0a0a'
      }}>
        <div style={{ color: '#ffffff', fontSize: '1.2rem', fontWeight: 500 }}>Loading...</div>
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
      background: '#0a0a0a',
      padding: '2rem'
    }}>
      <div style={{
        background: '#333333',
        borderRadius: '20px',
        padding: '3rem',
        maxWidth: '450px',
        width: '100%',
        boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3), 0 2px 8px rgba(0, 0, 0, 0.2)',
        border: '1px solid #333333',
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
            alt="Dr. Anthony Chaffee" 
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
          Ask Dr. Chaffee
        </h1>

        <p style={{
          color: '#b0b0b0',
          marginBottom: '2rem',
          fontSize: '1rem'
        }}>
          Interactive Knowledge Base
        </p>

        <div style={{
          background: '#1a1a1a',
          padding: '1rem',
          borderRadius: '12px',
          marginBottom: '2rem',
          border: '1px solid #333333'
        }}>
          <p style={{
            color: '#b0b0b0',
            fontSize: '0.9rem',
            margin: 0
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

        <div style={{
          marginTop: '1.5rem',
          paddingTop: '1.5rem',
          borderTop: '1px solid #e2e8f0'
        }}>
          <p style={{
            color: '#64748b',
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
              padding: '0.75rem 1.5rem',
              fontSize: '0.9rem',
              fontWeight: 600,
              color: '#ffffff',
              background: '#f5f5f5',
              border: '2px solid #000000',
              borderRadius: '12px',
              textDecoration: 'none',
              cursor: 'pointer',
              transition: 'all 0.2s'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = '#000000';
              e.currentTarget.style.color = 'white';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = '#f5f5f5';
              e.currentTarget.style.color = '#000000';
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
          Based on Anthony Chaffee's content
        </p>
      </div>
    </div>
  );
}
