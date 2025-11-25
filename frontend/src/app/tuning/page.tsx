'use client';

import { useState, useEffect } from 'react';
import { Database, TrendingUp, AlertCircle, CheckCircle } from 'lucide-react';

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

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      const res = await fetch('/api/stats');
      const data = await res.json();
      setStats(data);
    } catch (error) {
      console.error('Failed to load stats:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <p style={{ color: '#6b7280' }}>Loading stats...</p>
      </div>
    );
  }

  if (!stats) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <p style={{ color: '#dc2626' }}>Failed to load stats</p>
      </div>
    );
  }

  const coveragePct = parseFloat(stats.embedding_coverage);
  const isCoverageGood = coveragePct >= 95;

  return (
    <div style={{ padding: '2rem' }}>
      {/* Header */}
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '2rem', fontWeight: 700, color: '#1f2937', marginBottom: '0.5rem' }}>
          Dashboard Overview
        </h1>
        <p style={{ color: '#6b7280' }}>
          Real-time statistics and embedding coverage
        </p>
      </div>

      {/* Stats Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
        {/* Total Videos */}
        <div style={{
          background: '#1a1a1a',
          borderRadius: '1rem',
          padding: '1.5rem',
          color: 'white',
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)',
          border: '1px solid #2a2a2a'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
            <Database style={{ width: '1.5rem', height: '1.5rem', opacity: 0.8 }} />
            <span style={{ fontSize: '0.875rem', fontWeight: 500, opacity: 0.9 }}>Videos</span>
          </div>
          <div style={{ fontSize: '2.25rem', fontWeight: 700, marginBottom: '0.5rem' }}>
            {stats.total_videos.toLocaleString()}
          </div>
          <div style={{ fontSize: '0.875rem', opacity: 0.8 }}>Total Videos Indexed</div>
        </div>

        {/* Total Segments */}
        <div style={{
          background: '#2a2a2a',
          borderRadius: '1rem',
          padding: '1.5rem',
          color: 'white',
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.3)',
          border: '1px solid #3a3a3a'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
            <TrendingUp style={{ width: '1.5rem', height: '1.5rem', opacity: 0.8 }} />
            <span style={{ fontSize: '0.875rem', fontWeight: 500, opacity: 0.9 }}>Segments</span>
          </div>
          <div style={{ fontSize: '2.25rem', fontWeight: 700, marginBottom: '0.5rem' }}>
            {stats.total_segments.toLocaleString()}
          </div>
          <div style={{ fontSize: '0.875rem', opacity: 0.8 }}>Total Segments</div>
        </div>

        {/* Embedding Coverage */}
        <div style={{
          background: '#0a0a0a',
          borderRadius: '1rem',
          padding: '1.5rem',
          color: 'white',
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.4)',
          border: '1px solid #1a1a1a'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
            {isCoverageGood ? (
              <CheckCircle style={{ width: '1.5rem', height: '1.5rem', opacity: 0.8 }} />
            ) : (
              <AlertCircle style={{ width: '1.5rem', height: '1.5rem', opacity: 0.8 }} />
            )}
            <span style={{ fontSize: '0.875rem', fontWeight: 500, opacity: 0.9 }}>Embedding Coverage</span>
          </div>
          <div style={{ fontSize: '2.25rem', fontWeight: 700, marginBottom: '0.5rem' }}>
            {stats.embedding_coverage}
          </div>
          <div style={{ fontSize: '0.875rem', opacity: 0.8 }}>
            {stats.segments_with_embeddings.toLocaleString()} of {stats.total_segments.toLocaleString()} segments
          </div>
        </div>
      </div>

      {/* Missing Embeddings Alert */}
      {stats.segments_missing_embeddings > 0 && (
        <div style={{
          background: '#f5f5f5',
          border: '1px solid #e0e0e0',
          borderRadius: '0.75rem',
          padding: '1.5rem',
          marginBottom: '2rem'
        }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '1rem' }}>
            <AlertCircle style={{ width: '1.5rem', height: '1.5rem', color: '#666666', marginTop: '0.25rem', flexShrink: 0 }} />
            <div>
              <h3 style={{ fontSize: '1rem', fontWeight: 600, color: '#1a1a1a', marginBottom: '0.5rem' }}>
                Missing Embeddings
              </h3>
              <p style={{ color: '#4a4a4a', marginBottom: '0.75rem' }}>
                {stats.segments_missing_embeddings.toLocaleString()} segments don't have embeddings yet and won't be searchable.
              </p>
              <p style={{ color: '#4a4a4a', fontSize: '0.875rem' }}>
                Run the embedding pipeline to process these segments and improve search coverage.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Info Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.5rem' }}>
        {/* Embedding Info */}
        <div style={{
          background: 'white',
          border: '1px solid #e5e7eb',
          borderRadius: '0.75rem',
          padding: '1.5rem'
        }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 600, color: '#1f2937', marginBottom: '1rem' }}>
            Embedding Configuration
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <div>
              <p style={{ fontSize: '0.875rem', color: '#6b7280', marginBottom: '0.25rem' }}>Dimensions</p>
              <p style={{ fontSize: '1.25rem', fontWeight: 600, color: '#1f2937' }}>
                {stats.embedding_dimensions}
              </p>
            </div>
            <div style={{ paddingTop: '0.75rem', borderTop: '1px solid #e5e7eb' }}>
              <p style={{ fontSize: '0.875rem', color: '#6b7280' }}>
                Embeddings help the AI find the most relevant clips. 384 is a good balance of speed and accuracy.
              </p>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div style={{
          background: 'white',
          border: '1px solid #e5e7eb',
          borderRadius: '0.75rem',
          padding: '1.5rem'
        }}>
          <h3 style={{ fontSize: '1rem', fontWeight: 600, color: '#1f2937', marginBottom: '1rem' }}>
            Quick Actions
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            <a
              href="/tuning/models"
              style={{
                display: 'inline-block',
                padding: '0.75rem 1rem',
                background: '#000000',
                color: 'white',
                borderRadius: '0.5rem',
                textDecoration: 'none',
                fontWeight: 500,
                fontSize: '0.875rem',
                textAlign: 'center',
                cursor: 'pointer',
                transition: 'background 0.2s'
              }}
              onMouseEnter={(e) => e.currentTarget.style.background = '#333333'}
              onMouseLeave={(e) => e.currentTarget.style.background = '#000000'}
            >
              View Embedding Models
            </a>
            <a
              href="/tuning/search"
              style={{
                display: 'inline-block',
                padding: '0.75rem 1rem',
                background: '#333333',
                color: 'white',
                borderRadius: '0.5rem',
                textDecoration: 'none',
                fontWeight: 500,
                fontSize: '0.875rem',
                textAlign: 'center',
                cursor: 'pointer',
                transition: 'background 0.2s'
              }}
              onMouseEnter={(e) => e.currentTarget.style.background = '#555555'}
              onMouseLeave={(e) => e.currentTarget.style.background = '#333333'}
            >
              Configure Search
            </a>
            <a
              href="/tuning/instructions"
              style={{
                display: 'inline-block',
                padding: '0.75rem 1rem',
                background: '#555555',
                color: 'white',
                borderRadius: '0.5rem',
                textDecoration: 'none',
                fontWeight: 500,
                fontSize: '0.875rem',
                textAlign: 'center',
                cursor: 'pointer',
                transition: 'background 0.2s'
              }}
              onMouseEnter={(e) => e.currentTarget.style.background = '#777777'}
              onMouseLeave={(e) => e.currentTarget.style.background = '#555555'}
            >
              Custom Instructions
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
