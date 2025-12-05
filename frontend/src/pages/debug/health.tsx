/**
 * Debug Health Check Page
 * 
 * This page provides a simple way to verify the app is working correctly.
 * It always renders content (never blank) and shows the status of API calls.
 * 
 * IMPORTANT: This page bypasses PasswordGate by using getLayout pattern.
 * If this page is blank, there's a fundamental React/Next.js issue.
 * If it shows errors, the API calls are failing.
 */

import { useState, useEffect, ReactElement } from 'react';
import Head from 'next/head';
import type { NextPageWithLayout } from '../_app';

interface HealthStatus {
  loading: boolean;
  stats: any | null;
  statsError: string | null;
  authCheck: any | null;
  authCheckError: string | null;
  discordStatus: any | null;
  discordStatusError: string | null;
  timestamp: string;
  clientRendered: boolean;
}

const DebugHealth: NextPageWithLayout = () => {
  const [status, setStatus] = useState<HealthStatus>({
    loading: true,
    stats: null,
    statsError: null,
    authCheck: null,
    authCheckError: null,
    discordStatus: null,
    discordStatusError: null,
    timestamp: new Date().toISOString(),
    clientRendered: false,
  });

  useEffect(() => {
    console.info('[DebugHealth] Component mounted, starting health checks');
    
    const checkHealth = async () => {
      const newStatus: HealthStatus = {
        loading: false,
        stats: null,
        statsError: null,
        authCheck: null,
        authCheckError: null,
        discordStatus: null,
        discordStatusError: null,
        timestamp: new Date().toISOString(),
        clientRendered: true,
      };

      // Check /api/stats
      try {
        console.info('[DebugHealth] Fetching /api/stats...');
        const statsRes = await fetch('/api/stats', {
          signal: AbortSignal.timeout(10000),
        });
        console.info('[DebugHealth] /api/stats response:', statsRes.status);
        if (statsRes.ok) {
          newStatus.stats = await statsRes.json();
        } else {
          newStatus.statsError = `HTTP ${statsRes.status}: ${statsRes.statusText}`;
        }
      } catch (err: any) {
        console.error('[DebugHealth] /api/stats error:', err);
        newStatus.statsError = err.message || 'Failed to fetch';
      }

      // Check /api/auth/check
      try {
        console.info('[DebugHealth] Fetching /api/auth/check...');
        const authRes = await fetch('/api/auth/check', {
          signal: AbortSignal.timeout(5000),
        });
        console.info('[DebugHealth] /api/auth/check response:', authRes.status);
        if (authRes.ok) {
          newStatus.authCheck = await authRes.json();
        } else {
          newStatus.authCheckError = `HTTP ${authRes.status}: ${authRes.statusText}`;
        }
      } catch (err: any) {
        console.error('[DebugHealth] /api/auth/check error:', err);
        newStatus.authCheckError = err.message || 'Failed to fetch';
      }

      // Check /api/auth/discord/status
      try {
        console.info('[DebugHealth] Fetching /api/auth/discord/status...');
        const discordRes = await fetch('/api/auth/discord/status', {
          signal: AbortSignal.timeout(5000),
        });
        console.info('[DebugHealth] /api/auth/discord/status response:', discordRes.status);
        if (discordRes.ok) {
          newStatus.discordStatus = await discordRes.json();
        } else {
          newStatus.discordStatusError = `HTTP ${discordRes.status}: ${discordRes.statusText}`;
        }
      } catch (err: any) {
        console.error('[DebugHealth] /api/auth/discord/status error:', err);
        newStatus.discordStatusError = err.message || 'Failed to fetch';
      }

      console.info('[DebugHealth] Health check complete:', newStatus);
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
          <h2 style={{ color: '#60a5fa', fontSize: '1.25rem' }}>🎮 Discord Status (/api/auth/discord/status)</h2>
          {status.discordStatusError ? (
            <div style={{ 
              backgroundColor: '#7f1d1d', 
              padding: '1rem', 
              borderRadius: '8px',
              marginTop: '0.5rem'
            }}>
              <strong>❌ Error:</strong> {status.discordStatusError}
            </div>
          ) : status.discordStatus ? (
            <pre style={{ 
              backgroundColor: '#1e3a1e', 
              padding: '1rem', 
              borderRadius: '8px',
              overflow: 'auto',
              marginTop: '0.5rem'
            }}>
              {JSON.stringify(status.discordStatus, null, 2)}
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
              <strong>Client Rendered:</strong> {status.clientRendered ? '✅ Yes' : '❌ No (SSR only)'}
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
};

// This page bypasses PasswordGate - it renders directly without auth check
DebugHealth.getLayout = (page: ReactElement) => page;

export default DebugHealth;
