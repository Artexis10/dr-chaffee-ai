'use client';

import { useState, useEffect, useCallback } from 'react';
import { Calendar, RefreshCw, AlertCircle, FileText, TrendingUp, Clock, DollarSign, Users, CheckCircle, XCircle, ThumbsUp, ThumbsDown, MessageSquare } from 'lucide-react';
import '../tuning-pages.css';
import { apiFetch } from '@/utils/api';

interface FeedbackSummary {
  total: number;
  positive: number;
  negative: number;
  by_model?: Record<string, { positive: number; negative: number }>;
  top_tags?: Array<{ tag: string; count: number }>;
}

interface SummaryStats {
  queries: number;
  answers: number;
  searches: number;
  distinct_sessions: number;
  total_tokens: number;
  avg_tokens: number;
  total_cost_usd: number;
  avg_latency_ms: number;
  success_rate: number;
  success_count: number;
  error_count: number;
  feedback_summary?: FeedbackSummary;
}

interface SummaryListItem {
  id: string;
  summary_date: string;
  stats: SummaryStats;
  created_at: string;
  updated_at: string | null;
}

interface SummaryDetail extends SummaryListItem {
  summary_text: string;
  summary_html: string | null;
}

export default function SummariesPage() {
  const [summaries, setSummaries] = useState<SummaryListItem[]>([]);
  const [selectedSummary, setSelectedSummary] = useState<SummaryDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadSummaries = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await apiFetch('/api/admin/daily-summaries?limit=30');
      if (!res.ok) {
        if (res.status === 401) {
          throw new Error('Authentication required. Please log in to the tuning dashboard.');
        }
        throw new Error(`Failed to load summaries: ${res.status}`);
      }
      const data = await res.json();
      setSummaries(data);
    } catch (err) {
      console.error('Failed to load summaries:', err);
      setError(err instanceof Error ? err.message : 'Failed to load summaries');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadSummaryDetail = useCallback(async (date: string) => {
    try {
      const res = await apiFetch(`/api/admin/daily-summaries/${date}`);
      if (!res.ok) {
        throw new Error(`Failed to load summary: ${res.status}`);
      }
      const data = await res.json();
      setSelectedSummary(data);
    } catch (err) {
      console.error('Failed to load summary detail:', err);
      setError(err instanceof Error ? err.message : 'Failed to load summary');
    }
  }, []);

  const generateSummary = useCallback(async (date?: string) => {
    setGenerating(true);
    setError(null);
    try {
      const res = await apiFetch('/api/admin/daily-summaries/generate', {
        method: 'POST',
        body: JSON.stringify({ summary_date: date, force_regenerate: false }),
      });
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(errorData.detail || `Failed to generate: ${res.status}`);
      }
      const data = await res.json();
      setSelectedSummary(data);
      // Refresh list
      await loadSummaries();
    } catch (err) {
      console.error('Failed to generate summary:', err);
      setError(err instanceof Error ? err.message : 'Failed to generate summary');
    } finally {
      setGenerating(false);
    }
  }, [loadSummaries]);

  useEffect(() => {
    loadSummaries();
  }, [loadSummaries]);

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { 
      weekday: 'short', 
      month: 'short', 
      day: 'numeric',
      year: 'numeric'
    });
  };

  const formatCost = (cost: number) => {
    return cost < 0.01 ? '<$0.01' : `$${cost.toFixed(2)}`;
  };

  if (loading) {
    return (
      <div className="tuning-page tuning-centered">
        <p className="tuning-text-muted">Loading summaries...</p>
      </div>
    );
  }

  return (
    <div className="tuning-page">
      {/* Header */}
      <div className="tuning-header">
        <div>
          <h1 className="tuning-title">Daily Summaries</h1>
          <p className="tuning-text-muted">AI-generated usage digests for admin review</p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button 
            onClick={() => generateSummary()} 
            className="tuning-btn tuning-btn-primary"
            disabled={generating}
            title="Generate summary for yesterday"
          >
            {generating ? 'Generating...' : 'Generate Yesterday'}
          </button>
          <button 
            onClick={() => loadSummaries()} 
            className="tuning-btn tuning-btn-secondary"
            title="Refresh list"
            disabled={loading}
          >
            <RefreshCw style={{ width: 16, height: 16 }} />
          </button>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="tuning-alert tuning-alert-error">
          <AlertCircle style={{ width: 20, height: 20 }} />
          {error}
        </div>
      )}

      {/* Main Content */}
      <div className="tuning-grid-2">
        {/* Summaries List */}
        <div className="tuning-card">
          <h3 className="tuning-card-title">Recent Summaries</h3>
          {summaries.length === 0 ? (
            <p className="tuning-text-muted" style={{ textAlign: 'center', padding: '2rem 0' }}>
              No summaries yet. Click "Generate Yesterday" to create one.
            </p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {summaries.map((summary) => (
                <button
                  key={summary.id}
                  onClick={() => loadSummaryDetail(summary.summary_date)}
                  className={`tuning-btn ${selectedSummary?.id === summary.id ? 'tuning-btn-primary' : 'tuning-btn-secondary'}`}
                  style={{ 
                    textAlign: 'left', 
                    display: 'flex', 
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '0.75rem 1rem'
                  }}
                >
                  <span style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <Calendar style={{ width: 14, height: 14 }} />
                    {formatDate(summary.summary_date)}
                  </span>
                  <span style={{ fontSize: '0.75rem', opacity: 0.7 }}>
                    {summary.stats.queries} queries
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Summary Detail */}
        <div className="tuning-card">
          <h3 className="tuning-card-title">
            {selectedSummary ? `Summary: ${formatDate(selectedSummary.summary_date)}` : 'Select a Summary'}
          </h3>
          
          {selectedSummary ? (
            <>
              {/* Stats Grid */}
              <div style={{ 
                display: 'grid', 
                gridTemplateColumns: 'repeat(auto-fit, minmax(100px, 1fr))', 
                gap: '0.75rem',
                marginBottom: '1.5rem'
              }}>
                <div style={{ textAlign: 'center', padding: '0.75rem', background: 'var(--bg-card-elevated)', borderRadius: '0.5rem' }}>
                  <TrendingUp style={{ width: 16, height: 16, marginBottom: '0.25rem', opacity: 0.7 }} />
                  <div style={{ fontSize: '1.25rem', fontWeight: 700 }}>{selectedSummary.stats.queries}</div>
                  <div style={{ fontSize: '0.7rem', opacity: 0.7 }}>Queries</div>
                </div>
                <div style={{ textAlign: 'center', padding: '0.75rem', background: 'var(--bg-card-elevated)', borderRadius: '0.5rem' }}>
                  <Users style={{ width: 16, height: 16, marginBottom: '0.25rem', opacity: 0.7 }} />
                  <div style={{ fontSize: '1.25rem', fontWeight: 700 }}>{selectedSummary.stats.distinct_sessions}</div>
                  <div style={{ fontSize: '0.7rem', opacity: 0.7 }}>Sessions</div>
                </div>
                <div style={{ textAlign: 'center', padding: '0.75rem', background: 'var(--bg-card-elevated)', borderRadius: '0.5rem' }}>
                  <DollarSign style={{ width: 16, height: 16, marginBottom: '0.25rem', opacity: 0.7 }} />
                  <div style={{ fontSize: '1.25rem', fontWeight: 700 }}>{formatCost(selectedSummary.stats.total_cost_usd)}</div>
                  <div style={{ fontSize: '0.7rem', opacity: 0.7 }}>Cost</div>
                </div>
                <div style={{ textAlign: 'center', padding: '0.75rem', background: 'var(--bg-card-elevated)', borderRadius: '0.5rem' }}>
                  <Clock style={{ width: 16, height: 16, marginBottom: '0.25rem', opacity: 0.7 }} />
                  <div style={{ fontSize: '1.25rem', fontWeight: 700 }}>{Math.round(selectedSummary.stats.avg_latency_ms)}ms</div>
                  <div style={{ fontSize: '0.7rem', opacity: 0.7 }}>Avg Latency</div>
                </div>
                <div style={{ textAlign: 'center', padding: '0.75rem', background: 'var(--bg-card-elevated)', borderRadius: '0.5rem' }}>
                  {selectedSummary.stats.success_rate >= 0.95 ? (
                    <CheckCircle style={{ width: 16, height: 16, marginBottom: '0.25rem', color: '#22c55e' }} />
                  ) : (
                    <XCircle style={{ width: 16, height: 16, marginBottom: '0.25rem', color: '#ef4444' }} />
                  )}
                  <div style={{ fontSize: '1.25rem', fontWeight: 700 }}>{(selectedSummary.stats.success_rate * 100).toFixed(0)}%</div>
                  <div style={{ fontSize: '0.7rem', opacity: 0.7 }}>Success</div>
                </div>
              </div>

              {/* Feedback Summary */}
              {selectedSummary.stats.feedback_summary && (
                <div style={{ 
                  background: 'var(--bg-card-elevated)', 
                  borderRadius: '0.5rem', 
                  padding: '1rem',
                  marginBottom: '1rem'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
                    <MessageSquare style={{ width: 16, height: 16, opacity: 0.7 }} />
                    <span style={{ fontWeight: 600, fontSize: '0.875rem' }}>User Feedback</span>
                  </div>
                  
                  <div style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap', marginBottom: '0.75rem' }}>
                    <span style={{ fontSize: '0.875rem' }}>
                      {selectedSummary.stats.feedback_summary.total} total
                    </span>
                    <span style={{ fontSize: '0.875rem', color: '#22c55e', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                      <ThumbsUp style={{ width: 14, height: 14 }} />
                      {selectedSummary.stats.feedback_summary.positive}
                    </span>
                    <span style={{ fontSize: '0.875rem', color: '#ef4444', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                      <ThumbsDown style={{ width: 14, height: 14 }} />
                      {selectedSummary.stats.feedback_summary.negative}
                    </span>
                  </div>

                  {/* Per-model breakdown */}
                  {selectedSummary.stats.feedback_summary.by_model && 
                   Object.keys(selectedSummary.stats.feedback_summary.by_model).length > 0 && (
                    <div style={{ marginTop: '0.5rem', paddingTop: '0.5rem', borderTop: '1px solid var(--border-subtle)' }}>
                      <div style={{ fontSize: '0.75rem', opacity: 0.7, marginBottom: '0.5rem' }}>By Model</div>
                      {Object.entries(selectedSummary.stats.feedback_summary.by_model).map(([model, counts]) => (
                        <div key={model} style={{ 
                          display: 'flex', 
                          justifyContent: 'space-between', 
                          fontSize: '0.8rem',
                          padding: '0.25rem 0'
                        }}>
                          <span style={{ opacity: 0.8 }}>{model}</span>
                          <span>
                            <span style={{ color: '#22c55e' }}>👍 {counts.positive}</span>
                            {' / '}
                            <span style={{ color: '#ef4444' }}>👎 {counts.negative}</span>
                          </span>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Top tags */}
                  {selectedSummary.stats.feedback_summary.top_tags && 
                   selectedSummary.stats.feedback_summary.top_tags.length > 0 && (
                    <div style={{ marginTop: '0.5rem', paddingTop: '0.5rem', borderTop: '1px solid var(--border-subtle)' }}>
                      <div style={{ fontSize: '0.75rem', opacity: 0.7, marginBottom: '0.5rem' }}>Top Issues</div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                        {selectedSummary.stats.feedback_summary.top_tags.map((t) => (
                          <span key={t.tag} style={{ 
                            fontSize: '0.75rem', 
                            padding: '0.25rem 0.5rem', 
                            background: 'var(--bg-body)', 
                            borderRadius: '0.25rem' 
                          }}>
                            {t.tag} ({t.count})
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Summary Text */}
              <div style={{ 
                background: 'var(--bg-card-elevated)', 
                borderRadius: '0.5rem', 
                padding: '1rem',
                maxHeight: '500px',
                overflowY: 'auto'
              }}>
                <div style={{ 
                  whiteSpace: 'pre-wrap', 
                  fontSize: '0.875rem', 
                  lineHeight: 1.6,
                  color: 'var(--text-primary)'
                }}>
                  {selectedSummary.summary_text}
                </div>
              </div>

              {/* Metadata */}
              <div style={{ marginTop: '1rem', fontSize: '0.75rem', opacity: 0.6 }}>
                Generated: {new Date(selectedSummary.created_at).toLocaleString()}
                {selectedSummary.updated_at && selectedSummary.updated_at !== selectedSummary.created_at && (
                  <> · Updated: {new Date(selectedSummary.updated_at).toLocaleString()}</>
                )}
              </div>
            </>
          ) : (
            <div style={{ textAlign: 'center', padding: '3rem 1rem' }}>
              <FileText style={{ width: 48, height: 48, opacity: 0.3, marginBottom: '1rem' }} />
              <p className="tuning-text-muted">
                Select a date from the list to view its summary, or generate a new one.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
