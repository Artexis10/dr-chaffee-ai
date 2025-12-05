/**
 * Debug Health Check Page
 * 
 * This page provides a simple way to verify the app is working correctly.
 * It always renders content (never blank) and shows the status of API calls.
 * 
 * Use this to debug production issues - if this page is blank, there's a
 * fundamental rendering issue. If it shows errors, the API calls are failing.
 */

import { useState, useEffect } from 'react';
import Head from 'next/head';

interface HealthStatus {
  loading: boolean;
  stats: any | null;
  statsError: string | null;
  authCheck: any | null;
  authCheckError: string | null;
  timestamp: string;
}

export default function DebugHealth() {
  const [status, setStatus] = useState<HealthStatus>({
    loading: true,
    stats: null,
    statsError: null,
    authCheck: null,
    authCheckError: null,
    timestamp: new Date().toISOString(),
  });

  useEffect(() => {
    const checkHealth = async () => {
      const newStatus: HealthStatus = {
        loading: false,
        stats: null,
        statsError: null,
        authCheck: null,
        authCheckError: null,
        timestamp: new Date().toISOString(),
      };

      // Check /api/stats
      try {
        const statsRes = await fetch('/api/stats', {
          signal: AbortSignal.timeout(10000),
        });
        if (statsRes.ok) {
          newStatus.stats = await statsRes.json();
        } else {
          newStatus.statsError = `HTTP ${statsRes.status}: ${statsRes.statusText}`;
        }
      } catch (err: any) {
        newStatus.statsError = err.message || 'Failed to fetch';
      }

      // Check /api/auth/check
      try {
        const authRes = await fetch('/api/auth/check', {
          signal: AbortSignal.timeout(5000),
        });
        if (authRes.ok) {
          newStatus.authCheck = await authRes.json();
        } else {
          newStatus.authCheckError = `HTTP ${authRes.status}: ${authRes.statusText}`;
        }
      } catch (err: any) {
        newStatus.authCheckError = err.message || 'Failed to fetch';
      }

      setStatus(newStatus);
    };

    checkHealth();
  }, []);

  return (
    <>
      <Head>
        <title>Debug Health Check | Ask Dr Chaffee</title>
      </Head>
      <div style={{
        fontFamily: 'system-ui, -apple-system, sans-serif',
        padding: '2rem',
        maxWidth: '800px',
        margin: '0 auto',
        backgroundColor: '#1a1a1a',
        color: '#e0e0e0',
        minHeight: '100vh',
      }}>
        <h1 style={{ color: '#4ade80', marginBottom: '1rem' }}>🏥 Debug Health Check</h1>
        
        <p style={{ color: '#888', marginBottom: '2rem' }}>
          This page always renders content. If you see this text, React is working.
        </p>

        <div style={{ marginBottom: '2rem' }}>
          <h2 style={{ color: '#60a5fa', fontSize: '1.25rem' }}>📊 Status</h2>
          <ul style={{ listStyle: 'none', padding: 0 }}>
            <li style={{ padding: '0.5rem 0' }}>
              <strong>Timestamp:</strong> {status.timestamp}
            </li>
            <li style={{ padding: '0.5rem 0' }}>
              <strong>Loading:</strong> {status.loading ? '⏳ Yes' : '✅ Complete'}
            </li>
          </ul>
        </div>

        <div style={{ marginBottom: '2rem' }}>
          <h2 style={{ color: '#60a5fa', fontSize: '1.25rem' }}>🔐 Auth Check (/api/auth/check)</h2>
          {status.authCheckError ? (
            <div style={{ 
              backgroundColor: '#7f1d1d', 
              padding: '1rem', 
              borderRadius: '8px',
              marginTop: '0.5rem'
            }}>
              <strong>❌ Error:</strong> {status.authCheckError}
            </div>
          ) : status.authCheck ? (
            <pre style={{ 
              backgroundColor: '#1e3a1e', 
              padding: '1rem', 
              borderRadius: '8px',
              overflow: 'auto',
              marginTop: '0.5rem'
            }}>
              {JSON.stringify(status.authCheck, null, 2)}
            </pre>
          ) : (
            <p style={{ color: '#888' }}>Loading...</p>
          )}
        </div>

        <div style={{ marginBottom: '2rem' }}>
          <h2 style={{ color: '#60a5fa', fontSize: '1.25rem' }}>📈 Stats (/api/stats)</h2>
          {status.statsError ? (
            <div style={{ 
              backgroundColor: '#7f1d1d', 
              padding: '1rem', 
              borderRadius: '8px',
              marginTop: '0.5rem'
            }}>
              <strong>❌ Error:</strong> {status.statsError}
            </div>
          ) : status.stats ? (
            <pre style={{ 
              backgroundColor: '#1e3a1e', 
              padding: '1rem', 
              borderRadius: '8px',
              overflow: 'auto',
              marginTop: '0.5rem'
            }}>
              {JSON.stringify(status.stats, null, 2)}
            </pre>
          ) : (
            <p style={{ color: '#888' }}>Loading...</p>
          )}
        </div>

        <div style={{ marginBottom: '2rem' }}>
          <h2 style={{ color: '#60a5fa', fontSize: '1.25rem' }}>🌐 Environment</h2>
          <ul style={{ listStyle: 'none', padding: 0 }}>
            <li style={{ padding: '0.5rem 0' }}>
              <strong>NODE_ENV:</strong> {process.env.NODE_ENV || 'not set'}
            </li>
            <li style={{ padding: '0.5rem 0' }}>
              <strong>Build Time:</strong> {new Date().toISOString()}
            </li>
          </ul>
        </div>

        <div style={{ 
          marginTop: '2rem', 
          paddingTop: '1rem', 
          borderTop: '1px solid #333' 
        }}>
          <a 
            href="/" 
            style={{ 
              color: '#60a5fa', 
              textDecoration: 'none',
              marginRight: '1rem'
            }}
          >
            ← Back to Home
          </a>
          <button
            onClick={() => window.location.reload()}
            style={{
              backgroundColor: '#3b82f6',
              color: 'white',
              border: 'none',
              padding: '0.5rem 1rem',
              borderRadius: '4px',
              cursor: 'pointer',
            }}
          >
            🔄 Refresh
          </button>
        </div>
      </div>
    </>
  );
}
