'use client';

import { useState, useEffect } from 'react';
import Image from 'next/image';
import '../tuning-pages.css';
import { apiFetch } from '@/utils/api';
import { resetGlobalUnauthorized, invalidateAllTuningCaches } from '@/hooks/useTuningData';

// Theme constants - must match DarkModeToggle.tsx
const THEME_KEY = 'askdrchaffee.theme';

export default function TuningAuth() {
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [discordEnabled, setDiscordEnabled] = useState(false);
  const [discordLoading, setDiscordLoading] = useState(false);

  // Initialize theme on mount (default to DARK)
  useEffect(() => {
    const storedTheme = localStorage.getItem(THEME_KEY);
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    // Determine initial theme: stored > system preference > default DARK
    let shouldBeDark: boolean;
    if (storedTheme === 'dark') {
      shouldBeDark = true;
    } else if (storedTheme === 'light') {
      shouldBeDark = false;
    } else {
      // No stored preference - default to DARK unless system explicitly prefers light
      shouldBeDark = prefersDark !== false;
    }
    
    const root = document.documentElement;
    if (shouldBeDark) {
      root.classList.add('dark-mode');
      root.classList.remove('light-mode');
    } else {
      root.classList.remove('dark-mode');
      root.classList.add('light-mode');
    }
    
    // Persist if not already stored
    if (!storedTheme) {
      localStorage.setItem(THEME_KEY, shouldBeDark ? 'dark' : 'light');
    }
    
    // Check if Discord login is enabled (non-blocking)
    fetch('/api/auth/discord/status', { credentials: 'include' })
      .then(res => res.ok ? res.json() : { enabled: false })
      .then(d => setDiscordEnabled(d?.enabled === true))
      .catch(() => setDiscordEnabled(false));
  }, []);

  const handleDiscordLogin = () => {
    setDiscordLoading(true);
    setError('');
    // Redirect to Discord OAuth flow
    window.location.href = '/api/auth/discord/login';
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      console.log('[Tuning Auth Page] Submitting password...');
      // Validate password on backend (never expose password in frontend)
      const response = await apiFetch('/api/tuning/auth/verify', {
        method: 'POST',
        body: JSON.stringify({ password })
      });

      console.log('[Tuning Auth Page] Response status:', response.status);
      const data = await response.json();
      console.log('[Tuning Auth Page] Response data:', data);

      if (response.ok) {
        // Store main app token in localStorage for PasswordGate compatibility
        if (data.token) {
          localStorage.setItem('auth_token', data.token);
          console.log('[Tuning Auth Page] Main app token stored in localStorage');
        }
        
        // CRITICAL: Reset the global unauthorized flag and clear caches
        // This ensures useTuningData hooks will fetch fresh data after login
        resetGlobalUnauthorized();
        invalidateAllTuningCaches();
        console.log('[Tuning Auth Page] Reset unauthorized state and cleared caches');
        
        console.log('[Tuning Auth Page] Authentication successful, redirecting...');
        // Use window.location for full page navigation to ensure cookie is sent
        window.location.href = '/tuning';
      } else if (response.status === 401) {
        setError('Incorrect password');
        setPassword('');
      } else {
        setError(data.error || 'Authentication failed');
      }
    } catch (err: any) {
      console.error('[Tuning Auth Page] Error:', err);
      setError(err.message || 'Connection error');
    }

    setLoading(false);
  };

  return (
    <div className="tuning-auth-container">
      <div className="tuning-auth-card">
        <div className="tuning-auth-avatar">
          <Image 
            src="/dr-chaffee.jpg" 
            alt="Dr Anthony Chaffee" 
            width={120} 
            height={120}
            style={{ objectFit: 'cover' }}
          />
        </div>

        <h1 className="tuning-auth-title">Tuning Dashboard</h1>
        <p className="tuning-auth-subtitle">Admin Access Only</p>

        <div className="tuning-auth-notice">
          <p>🔒 This dashboard is for privileged users only. Enter your admin password to continue.</p>
        </div>

        <form onSubmit={handleSubmit}>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="Enter admin password"
            autoFocus
            disabled={loading || discordLoading}
            className={`tuning-auth-input ${error ? 'error' : ''}`}
          />

          {error && (
            <div className="tuning-auth-error">{error}</div>
          )}

          <button
            type="submit"
            disabled={loading || discordLoading}
            className="tuning-auth-submit"
          >
            {loading ? 'Unlocking...' : 'Access Dashboard'}
          </button>
        </form>

        {/* Discord Login - only shown when enabled */}
        {discordEnabled && (
          <div style={{ marginTop: '1.5rem', textAlign: 'center' }}>
            <p style={{ 
              color: 'var(--text-muted)', 
              fontSize: '0.875rem', 
              marginBottom: '0.75rem' 
            }}>
              — or —
            </p>
            <button
              onClick={handleDiscordLogin}
              disabled={loading || discordLoading}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '0.5rem',
                width: '100%',
                padding: '0.75rem 1rem',
                background: '#5865F2',
                color: 'white',
                border: 'none',
                borderRadius: '0.5rem',
                fontSize: '1rem',
                fontWeight: 600,
                cursor: loading || discordLoading ? 'not-allowed' : 'pointer',
                opacity: loading || discordLoading ? 0.7 : 1,
                transition: 'background 0.2s',
              }}
              onMouseEnter={(e) => {
                if (!loading && !discordLoading) {
                  e.currentTarget.style.background = '#4752C4';
                }
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = '#5865F2';
              }}
            >
              <svg width="20" height="20" viewBox="0 0 71 55" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M60.1045 4.8978C55.5792 2.8214 50.7265 1.2916 45.6527 0.41542C45.5603 0.39851 45.468 0.440769 45.4204 0.525289C44.7963 1.6353 44.105 3.0834 43.6209 4.2216C38.1637 3.4046 32.7345 3.4046 27.3892 4.2216C26.905 3.0581 26.1886 1.6353 25.5617 0.525289C25.5141 0.443589 25.4218 0.40133 25.3294 0.41542C20.2584 1.2888 15.4057 2.8186 10.8776 4.8978C10.8384 4.9147 10.8048 4.9429 10.7825 4.9795C1.57795 18.7309 -0.943561 32.1443 0.293408 45.3914C0.299005 45.4562 0.335386 45.5182 0.385761 45.5576C6.45866 50.0174 12.3413 52.7249 18.1147 54.5195C18.2071 54.5477 18.305 54.5139 18.3638 54.4378C19.7295 52.5728 20.9469 50.6063 21.9907 48.5383C22.0523 48.4172 21.9935 48.2735 21.8676 48.2256C19.9366 47.4931 18.0979 46.6 16.3292 45.5858C16.1893 45.5041 16.1781 45.304 16.3068 45.2082C16.679 44.9293 17.0513 44.6391 17.4067 44.3461C17.471 44.2926 17.5606 44.2813 17.6362 44.3151C29.2558 49.6202 41.8354 49.6202 53.3179 44.3151C53.3## 44.2785 53.4831 44.2898 53.5502 44.3433C53.9057 44.6363 54.2779 44.9293 54.6529 45.2082C54.7816 45.304 54.7732 45.5041 54.6333 45.5858C52.8646 46.6197 51.0259 47.4931 49.0921 48.2228C48.9662 48.2707 48.9102 48.4172 48.9718 48.5383C50.038 50.6034 51.2554 52.5699 52.5959 54.435C52.6519 54.5139 52.7526 54.5477 52.845 54.5195C58.6464 52.7249 64.529 50.0174 70.6019 45.5576C70.6551 45.5182 70.6887 45.459 70.6943 45.3942C72.1747 30.0791 68.2147 16.7757 60.1968 4.9823C60.1772 4.9429 60.1437 4.9147 60.1045 4.8978ZM23.7259 37.3253C20.2276 37.3253 17.3451 34.1136 17.3451 30.1693C17.3451 26.225 20.1717 23.0133 23.7259 23.0133C27.308 23.0133 30.1626 26.2532 30.1099 30.1693C30.1099 34.1136 27.2802 37.3253 23.7259 37.3253ZM47.3178 37.3253C43.8196 37.3253 40.9371 34.1136 40.9371 30.1693C40.9371 26.225 43.7680 23.0133 47.3178 23.0133C50.8999 23.0133 53.7545 26.2532 53.7018 30.1693C53.7018 34.1136 50.8999 37.3253 47.3178 37.3253Z" fill="currentColor"/>
              </svg>
              {discordLoading ? 'Redirecting...' : 'Log in with Discord'}
            </button>
          </div>
        )}

        <div className="tuning-auth-footer">
          <a href="/" className="tuning-auth-back">Back to Main App</a>
        </div>
      </div>
    </div>
  );
}
