'use client';

import { useState, useEffect, useCallback } from 'react';
import { Database, TrendingUp, AlertCircle, CheckCircle, RefreshCw } from 'lucide-react';
import Link from 'next/link';
import './tuning-pages.css';
import { apiFetch } from '@/utils/api';

interface Stats {
  total_videos: number;
  total_segments: number;
  segments_with_embeddings: number;
  segments_missing_embeddings: number;
  embedding_coverage: string;
  embedding_dimensions: number;
}

export default function OverviewPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadStats = useCallback(async () => {
    setLoading(true);
    try {
      const res = await apiFetch('/api/stats');
      if (!res.ok) {
        throw new Error(`Failed to load stats: ${res.status}`);
      }
      const data = await res.json();
      setStats(data);
      setError(null);
    } catch (err) {
      console.error('Failed to load stats:', err);
      setError(err instanceof Error ? err.message : 'Failed to load stats');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  if (loading) {
    return (
      <div className="tuning-page tuning-centered">
        <p className="tuning-text-muted">Loading stats...</p>
      </div>
    );
  }

  if (error || !stats) {
    return (
      <div className="tuning-page">
        <div className="tuning-alert tuning-alert-error">
          <AlertCircle style={{ width: 20, height: 20 }} />
          {error || 'Failed to load stats'}
        </div>
      </div>
    );
  }

  const coveragePct = parseFloat(stats.embedding_coverage);
  const isCoverageGood = coveragePct >= 95;

  return (
    <div className="tuning-page">
      {/* Header */}
      <div className="tuning-header">
        <div>
          <h1 className="tuning-title">Dashboard Overview</h1>
          <p className="tuning-text-muted">Real-time statistics and embedding coverage</p>
        </div>
        <button 
          onClick={() => loadStats()} 
          className="tuning-btn tuning-btn-secondary"
          title="Refresh stats"
          disabled={loading}
        >
          <RefreshCw style={{ width: 16, height: 16 }} />
        </button>
      </div>

      {/* Stats Grid */}
      <div className="tuning-stats-grid">
        <div className="tuning-stat-card">
          <div className="tuning-stat-header">
            <Database style={{ width: 20, height: 20 }} />
            <span>Videos</span>
          </div>
          <div className="tuning-stat-value">{stats.total_videos.toLocaleString()}</div>
          <div className="tuning-stat-label">Total Videos Indexed</div>
        </div>

        <div className="tuning-stat-card">
          <div className="tuning-stat-header">
            <TrendingUp style={{ width: 20, height: 20 }} />
            <span>Segments</span>
          </div>
          <div className="tuning-stat-value">{stats.total_segments.toLocaleString()}</div>
          <div className="tuning-stat-label">Total Segments</div>
        </div>

        <div className="tuning-stat-card">
          <div className="tuning-stat-header">
            {isCoverageGood ? <CheckCircle style={{ width: 20, height: 20 }} /> : <AlertCircle style={{ width: 20, height: 20 }} />}
            <span>Coverage</span>
          </div>
          <div className="tuning-stat-value">{stats.embedding_coverage}</div>
          <div className="tuning-stat-label">
            {stats.segments_with_embeddings.toLocaleString()} of {stats.total_segments.toLocaleString()}
          </div>
        </div>
      </div>

      {/* Missing Embeddings Alert */}
      {stats.segments_missing_embeddings > 0 && (
        <div className="tuning-alert tuning-alert-warning">
          <AlertCircle style={{ width: 20, height: 20, flexShrink: 0, marginTop: 2 }} />
          <div>
            <p style={{ fontWeight: 600, marginBottom: 4 }}>Missing Embeddings</p>
            <p style={{ fontSize: '0.875rem', opacity: 0.9 }}>
              {stats.segments_missing_embeddings.toLocaleString()} segments don't have embeddings yet.
              Run the embedding pipeline to process these segments.
            </p>
          </div>
        </div>
      )}

      {/* Info Cards */}
      <div className="tuning-grid-2">
        <div className="tuning-card">
          <h3 className="tuning-card-title">Embedding Configuration</h3>
          <div style={{ marginBottom: 12 }}>
            <p className="tuning-text-muted" style={{ fontSize: '0.75rem', marginBottom: 4 }}>Dimensions</p>
            <p className="tuning-title" style={{ fontSize: '1.25rem' }}>{stats.embedding_dimensions}</p>
          </div>
          <p className="tuning-text-muted" style={{ fontSize: '0.875rem', paddingTop: 12, borderTop: '1px solid var(--border-subtle)' }}>
            Embeddings help the AI find the most relevant clips. 384 is a good balance of speed and accuracy.
          </p>
        </div>

        <div className="tuning-card">
          <h3 className="tuning-card-title">Quick Actions</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <Link href="/tuning/models" className="tuning-btn tuning-btn-primary">
              Configure Summarizer Model
            </Link>
            <Link href="/tuning/search" className="tuning-btn tuning-btn-secondary">
              Configure Search
            </Link>
            <Link href="/tuning/instructions" className="tuning-btn tuning-btn-secondary">
              Custom Instructions
            </Link>
            <Link href="/tuning/summaries" className="tuning-btn tuning-btn-secondary">
              Daily Summaries
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
