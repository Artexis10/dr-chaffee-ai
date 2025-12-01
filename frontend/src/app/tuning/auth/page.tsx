'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';
import '../tuning-pages.css';

// Theme constants - must match DarkModeToggle.tsx
const THEME_KEY = 'askdrchaffee.theme';

export default function TuningAuth() {
  const router = useRouter();
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

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
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      console.log('[Tuning Auth Page] Submitting password...');
      // Validate password on backend (never expose password in frontend)
      const response = await fetch('/api/tuning/auth/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',  // CRITICAL: Required to receive and store httpOnly cookies
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
        console.log('[Tuning Auth Page] Authentication successful, redirecting...');
        router.push('/tuning');
        router.refresh();
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
            alt="Dr. Anthony Chaffee" 
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
            disabled={loading}
            className={`tuning-auth-input ${error ? 'error' : ''}`}
          />

          {error && (
            <div className="tuning-auth-error">{error}</div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="tuning-auth-submit"
          >
            {loading ? 'Unlocking...' : 'Access Dashboard'}
          </button>
        </form>

        <div className="tuning-auth-footer">
          <a href="/" className="tuning-auth-back">Back to Main App</a>
        </div>
      </div>
    </div>
  );
}
