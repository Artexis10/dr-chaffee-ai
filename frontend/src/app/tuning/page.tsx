'use client';

import { useState, useEffect } from 'react';
import { Database, TrendingUp, AlertCircle, CheckCircle } from 'lucide-react';
import Link from 'next/link';

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

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      const res = await fetch('/api/stats');
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
  };

  if (loading) {
    return (
      <div className="tuning-page">
        <div className="tuning-loading">Loading stats...</div>
      </div>
    );
  }

  if (error || !stats) {
    return (
      <div className="tuning-page">
        <div className="tuning-message tuning-message-error">
          <AlertCircle />
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
      <div className="tuning-page-header">
        <h1 className="tuning-page-title">Dashboard Overview</h1>
        <p className="tuning-page-description">
          Real-time statistics and embedding coverage
        </p>
      </div>

      {/* Stats Grid */}
      <div className="tuning-stats-grid">
        {/* Total Videos */}
        <div className="tuning-stat-card">
          <div className="tuning-stat-header">
            <Database />
            <span className="tuning-stat-label">Videos</span>
          </div>
          <div className="tuning-stat-value">
            {stats.total_videos.toLocaleString()}
          </div>
          <div className="tuning-stat-description">Total Videos Indexed</div>
        </div>

        {/* Total Segments */}
        <div className="tuning-stat-card">
          <div className="tuning-stat-header">
            <TrendingUp />
            <span className="tuning-stat-label">Segments</span>
          </div>
          <div className="tuning-stat-value">
            {stats.total_segments.toLocaleString()}
          </div>
          <div className="tuning-stat-description">Total Segments</div>
        </div>

        {/* Embedding Coverage */}
        <div className="tuning-stat-card">
          <div className="tuning-stat-header">
            {isCoverageGood ? <CheckCircle /> : <AlertCircle />}
            <span className="tuning-stat-label">Embedding Coverage</span>
          </div>
          <div className="tuning-stat-value">
            {stats.embedding_coverage}
          </div>
          <div className="tuning-stat-description">
            {stats.segments_with_embeddings.toLocaleString()} of {stats.total_segments.toLocaleString()} segments
          </div>
        </div>
      </div>

      {/* Missing Embeddings Alert */}
      {stats.segments_missing_embeddings > 0 && (
        <div className="tuning-message tuning-message-warning" style={{ marginBottom: '2rem', alignItems: 'flex-start' }}>
          <AlertCircle style={{ marginTop: '0.125rem' }} />
          <div>
            <strong style={{ display: 'block', marginBottom: '0.25rem' }}>Missing Embeddings</strong>
            <span>
              {stats.segments_missing_embeddings.toLocaleString()} segments don't have embeddings yet and won't be searchable.
              Run the embedding pipeline to process these segments.
            </span>
          </div>
        </div>
      )}

      {/* Info Cards */}
      <div className="tuning-two-col">
        {/* Embedding Info */}
        <div className="tuning-card">
          <h3 className="tuning-card-title">Embedding Configuration</h3>
          <div className="tuning-form-group" style={{ marginBottom: 0 }}>
            <p className="tuning-input-hint" style={{ marginBottom: '0.25rem' }}>Dimensions</p>
            <p style={{ fontSize: '1.25rem', fontWeight: 600 }}>
              {stats.embedding_dimensions}
            </p>
          </div>
          <div style={{ paddingTop: '0.75rem', marginTop: '0.75rem', borderTop: '1px solid var(--border-subtle, #e5e7eb)' }}>
            <p className="tuning-input-hint">
              Embeddings help the AI find the most relevant clips. 384 is a good balance of speed and accuracy.
            </p>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="tuning-card">
          <h3 className="tuning-card-title">Quick Actions</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <Link href="/tuning/models" className="tuning-btn tuning-btn-primary">
              View Embedding Models
            </Link>
            <Link href="/tuning/search" className="tuning-btn tuning-btn-secondary">
              Configure Search
            </Link>
            <Link href="/tuning/instructions" className="tuning-btn tuning-btn-secondary">
              Custom Instructions
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
