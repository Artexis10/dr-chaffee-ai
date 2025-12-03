'use client';

/**
 * Admin Feedback View Page
 * 
 * Displays feedback events with filtering and pagination.
 * Protected by tuning auth (admin only).
 */

import { useState, useEffect, useCallback } from 'react';
import { RefreshCw, Filter, ChevronDown, ChevronUp, ThumbsUp, ThumbsDown, AlertCircle, MessageSquare } from 'lucide-react';
import '../tuning-pages.css';
import { apiFetch } from '@/utils/api';

interface FeedbackItem {
  id: string;
  target_type: string;
  target_id: string | null;
  rating: number | null;
  tags: string[] | null;
  comment: string | null;
  metadata: Record<string, any> | null;
  created_at: string;
  input_text_snippet: string | null;
  output_text_snippet: string | null;
  model_name: string | null;
}

interface FeedbackStats {
  by_type: Record<string, {
    total: number;
    positive: number;
    negative: number;
    neutral_or_broken: number;
    with_comments: number;
  }>;
  totals: {
    total: number;
    positive: number;
    negative: number;
  };
}

export default function FeedbackPage() {
  const [items, setItems] = useState<FeedbackItem[]>([]);
  const [stats, setStats] = useState<FeedbackStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  
  // Filters
  const [targetType, setTargetType] = useState<string>('');
  const [rating, setRating] = useState<string>('');
  const [fromDate, setFromDate] = useState<string>('');
  const [toDate, setToDate] = useState<string>('');
  
  const pageSize = 20;

  const loadFeedback = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      const params = new URLSearchParams();
      params.set('page', page.toString());
      params.set('page_size', pageSize.toString());
      
      if (targetType) params.set('target_type', targetType);
      if (rating) params.set('rating', rating);
      if (fromDate) params.set('from_date', fromDate);
      if (toDate) params.set('to_date', toDate);
      
      const res = await apiFetch(`/api/feedback?${params}`);
      
      if (!res.ok) {
        if (res.status === 401) {
          throw new Error('Authentication required');
        }
        throw new Error('Failed to load feedback');
      }
      
      const data = await res.json();
      setItems(data.items || []);
      setTotal(data.total || 0);
    } catch (err) {
      console.error('Failed to load feedback:', err);
      setError(err instanceof Error ? err.message : 'Failed to load feedback');
    } finally {
      setLoading(false);
    }
  }, [page, targetType, rating, fromDate, toDate]);

  const loadStats = useCallback(async () => {
    try {
      const params = new URLSearchParams();
      if (fromDate) params.set('from_date', fromDate);
      if (toDate) params.set('to_date', toDate);
      
      const res = await apiFetch(`/api/feedback/stats?${params}`);
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch (err) {
      console.error('Failed to load stats:', err);
    }
  }, [fromDate, toDate]);

  useEffect(() => {
    loadFeedback();
    loadStats();
  }, [loadFeedback, loadStats]);

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getRatingIcon = (rating: number | null) => {
    if (rating === 1) return <ThumbsUp className="rating-icon positive" />;
    if (rating === -1) return <ThumbsDown className="rating-icon negative" />;
    return <span className="rating-icon neutral">—</span>;
  };

  const getTypeLabel = (type: string) => {
    switch (type) {
      case 'answer': return 'Answer';
      case 'tuning_internal': return 'Tuning';
      case 'global': return 'Global';
      default: return type;
    }
  };

  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="tuning-page">
      {/* Header */}
      <div className="tuning-header">
        <div>
          <h1 className="tuning-title">Feedback</h1>
          <p className="tuning-text-muted">Review user feedback and ratings</p>
        </div>
        <button 
          onClick={() => { loadFeedback(); loadStats(); }} 
          className="tuning-btn tuning-btn-secondary"
          title="Refresh"
          disabled={loading}
        >
          <RefreshCw style={{ width: 16, height: 16 }} />
        </button>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="tuning-stats-grid" style={{ marginBottom: 24 }}>
          <div className="tuning-stat-card">
            <div className="tuning-stat-header">
              <MessageSquare style={{ width: 20, height: 20 }} />
              <span>Total</span>
            </div>
            <div className="tuning-stat-value">{stats.totals.total}</div>
            <div className="tuning-stat-label">All feedback</div>
          </div>
          <div className="tuning-stat-card">
            <div className="tuning-stat-header">
              <ThumbsUp style={{ width: 20, height: 20, color: '#22c55e' }} />
              <span>Positive</span>
            </div>
            <div className="tuning-stat-value">{stats.totals.positive}</div>
            <div className="tuning-stat-label">Thumbs up</div>
          </div>
          <div className="tuning-stat-card">
            <div className="tuning-stat-header">
              <ThumbsDown style={{ width: 20, height: 20, color: '#ef4444' }} />
              <span>Negative</span>
            </div>
            <div className="tuning-stat-value">{stats.totals.negative}</div>
            <div className="tuning-stat-label">Thumbs down</div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="tuning-card" style={{ marginBottom: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
          <Filter style={{ width: 16, height: 16 }} />
          <span className="tuning-label" style={{ marginBottom: 0 }}>Filters</span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 12 }}>
          <div>
            <label className="tuning-hint" style={{ display: 'block', marginBottom: 4 }}>Type</label>
            <select 
              value={targetType} 
              onChange={(e) => { setTargetType(e.target.value); setPage(1); }}
              className="tuning-input"
            >
              <option value="">All types</option>
              <option value="answer">Answer</option>
              <option value="tuning_internal">Tuning</option>
              <option value="global">Global</option>
            </select>
          </div>
          <div>
            <label className="tuning-hint" style={{ display: 'block', marginBottom: 4 }}>Rating</label>
            <select 
              value={rating} 
              onChange={(e) => { setRating(e.target.value); setPage(1); }}
              className="tuning-input"
            >
              <option value="">All ratings</option>
              <option value="1">Positive</option>
              <option value="-1">Negative</option>
            </select>
          </div>
          <div>
            <label className="tuning-hint" style={{ display: 'block', marginBottom: 4 }}>From</label>
            <input 
              type="date" 
              value={fromDate} 
              onChange={(e) => { setFromDate(e.target.value); setPage(1); }}
              className="tuning-input"
            />
          </div>
          <div>
            <label className="tuning-hint" style={{ display: 'block', marginBottom: 4 }}>To</label>
            <input 
              type="date" 
              value={toDate} 
              onChange={(e) => { setToDate(e.target.value); setPage(1); }}
              className="tuning-input"
            />
          </div>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="tuning-alert tuning-alert-error" style={{ marginBottom: 24 }}>
          <AlertCircle style={{ width: 20, height: 20 }} />
          {error}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="tuning-centered" style={{ padding: 48 }}>
          <p className="tuning-text-muted">Loading feedback...</p>
        </div>
      )}

      {/* Feedback List */}
      {!loading && items.length === 0 && (
        <div className="tuning-card" style={{ textAlign: 'center', padding: 48 }}>
          <p className="tuning-text-muted">No feedback found</p>
        </div>
      )}

      {!loading && items.length > 0 && (
        <div className="tuning-card" style={{ padding: 0 }}>
          <table className="feedback-table">
            <thead>
              <tr>
                <th style={{ width: 100 }}>Date</th>
                <th style={{ width: 80 }}>Type</th>
                <th style={{ width: 60 }}>Rating</th>
                <th>Tags / Comment</th>
                <th style={{ width: 40 }}></th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <>
                  <tr key={item.id} className={expandedId === item.id ? 'expanded' : ''}>
                    <td className="date-cell">{formatDate(item.created_at)}</td>
                    <td>
                      <span className={`type-badge type-${item.target_type}`}>
                        {getTypeLabel(item.target_type)}
                      </span>
                    </td>
                    <td className="rating-cell">{getRatingIcon(item.rating)}</td>
                    <td className="content-cell">
                      {item.tags && item.tags.length > 0 && (
                        <div className="tags-row">
                          {item.tags.map((tag, i) => (
                            <span key={i} className="feedback-tag">{tag}</span>
                          ))}
                        </div>
                      )}
                      {item.comment && (
                        <p className="comment-preview">
                          {item.comment.length > 100 
                            ? `${item.comment.substring(0, 100)}...` 
                            : item.comment}
                        </p>
                      )}
                      {!item.tags?.length && !item.comment && (
                        <span className="tuning-text-muted">No details</span>
                      )}
                    </td>
                    <td>
                      <button 
                        className="expand-btn"
                        onClick={() => setExpandedId(expandedId === item.id ? null : item.id)}
                      >
                        {expandedId === item.id ? <ChevronUp /> : <ChevronDown />}
                      </button>
                    </td>
                  </tr>
                  {expandedId === item.id && (
                    <tr className="detail-row">
                      <td colSpan={5}>
                        <div className="detail-content">
                          {item.target_type === 'answer' && (
                            <>
                              {item.input_text_snippet && (
                                <div className="detail-section">
                                  <label>Query:</label>
                                  <p>{item.input_text_snippet}</p>
                                </div>
                              )}
                              {item.output_text_snippet && (
                                <div className="detail-section">
                                  <label>Answer snippet:</label>
                                  <p>{item.output_text_snippet}</p>
                                </div>
                              )}
                              {item.model_name && (
                                <div className="detail-section">
                                  <label>Model:</label>
                                  <p>{item.model_name}</p>
                                </div>
                              )}
                            </>
                          )}
                          {item.comment && (
                            <div className="detail-section">
                              <label>Full comment:</label>
                              <p>{item.comment}</p>
                            </div>
                          )}
                          {item.metadata && Object.keys(item.metadata).length > 0 && (
                            <div className="detail-section">
                              <label>Metadata:</label>
                              <pre>{JSON.stringify(item.metadata, null, 2)}</pre>
                            </div>
                          )}
                          <div className="detail-section">
                            <label>ID:</label>
                            <code>{item.id}</code>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="pagination" style={{ marginTop: 24, display: 'flex', justifyContent: 'center', gap: 8 }}>
          <button 
            className="tuning-btn tuning-btn-secondary"
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
          >
            Previous
          </button>
          <span className="tuning-text-muted" style={{ padding: '8px 16px' }}>
            Page {page} of {totalPages}
          </span>
          <button 
            className="tuning-btn tuning-btn-secondary"
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
          >
            Next
          </button>
        </div>
      )}

      <style jsx>{`
        .feedback-table {
          width: 100%;
          border-collapse: collapse;
        }

        .feedback-table th,
        .feedback-table td {
          padding: 12px 16px;
          text-align: left;
          border-bottom: 1px solid var(--border-subtle, #262626);
        }

        .feedback-table th {
          font-size: 12px;
          font-weight: 600;
          color: var(--text-muted, #737373);
          text-transform: uppercase;
          letter-spacing: 0.05em;
          background: var(--bg-card-elevated, #1a1a1a);
        }

        .feedback-table tbody tr:hover {
          background: var(--bg-card-elevated, #1a1a1a);
        }

        .feedback-table tbody tr.expanded {
          background: var(--bg-card-elevated, #1a1a1a);
        }

        .date-cell {
          font-size: 13px;
          color: var(--text-muted, #737373);
          white-space: nowrap;
        }

        .type-badge {
          display: inline-block;
          padding: 4px 8px;
          font-size: 11px;
          font-weight: 600;
          border-radius: 4px;
          text-transform: uppercase;
        }

        .type-badge.type-answer {
          background: rgba(59, 130, 246, 0.1);
          color: #3b82f6;
        }

        .type-badge.type-tuning_internal {
          background: rgba(168, 85, 247, 0.1);
          color: #a855f7;
        }

        .type-badge.type-global {
          background: rgba(34, 197, 94, 0.1);
          color: #22c55e;
        }

        .rating-cell {
          text-align: center;
        }

        :global(.rating-icon) {
          width: 18px;
          height: 18px;
        }

        :global(.rating-icon.positive) {
          color: #22c55e;
        }

        :global(.rating-icon.negative) {
          color: #ef4444;
        }

        .rating-icon.neutral {
          color: var(--text-muted, #525252);
        }

        .content-cell {
          max-width: 400px;
        }

        .tags-row {
          display: flex;
          flex-wrap: wrap;
          gap: 4px;
          margin-bottom: 4px;
        }

        .feedback-tag {
          display: inline-block;
          padding: 2px 8px;
          font-size: 11px;
          font-weight: 500;
          border-radius: 10px;
          background: var(--bg-card-elevated, #262626);
          color: var(--text-light, #a3a3a3);
        }

        .comment-preview {
          margin: 0;
          font-size: 13px;
          color: var(--text-light, #d4d4d4);
          line-height: 1.4;
        }

        .expand-btn {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 28px;
          height: 28px;
          border: none;
          border-radius: 6px;
          background: transparent;
          color: var(--text-muted, #737373);
          cursor: pointer;
          transition: all 0.15s ease;
        }

        .expand-btn:hover {
          background: var(--bg-card-elevated, #262626);
          color: var(--text-light, #a3a3a3);
        }

        .detail-row td {
          padding: 0 !important;
          background: var(--bg-body, #0a0a0a);
        }

        .detail-content {
          padding: 16px 24px;
          border-left: 3px solid var(--border-subtle, #333);
          margin-left: 16px;
        }

        .detail-section {
          margin-bottom: 12px;
        }

        .detail-section:last-child {
          margin-bottom: 0;
        }

        .detail-section label {
          display: block;
          font-size: 11px;
          font-weight: 600;
          color: var(--text-muted, #737373);
          text-transform: uppercase;
          letter-spacing: 0.05em;
          margin-bottom: 4px;
        }

        .detail-section p {
          margin: 0;
          font-size: 13px;
          color: var(--text-light, #d4d4d4);
          line-height: 1.5;
        }

        .detail-section pre {
          margin: 0;
          padding: 8px 12px;
          font-size: 11px;
          background: var(--bg-card, #171717);
          border-radius: 6px;
          overflow-x: auto;
          color: var(--text-muted, #737373);
        }

        .detail-section code {
          font-size: 11px;
          color: var(--text-muted, #737373);
        }

        @media (max-width: 768px) {
          .feedback-table th:nth-child(4),
          .feedback-table td:nth-child(4) {
            display: none;
          }
        }
      `}</style>
    </div>
  );
}
