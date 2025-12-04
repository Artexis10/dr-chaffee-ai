/**
 * FeedbackStrip Component
 * 
 * Compact inline feedback UI for answer cards.
 * Shows thumbs up/down buttons with optional detailed feedback modal.
 * 
 * Follows existing design system: B&W theme, pill-styled buttons.
 */

import { useState } from 'react';
import { apiFetch } from '@/utils/api';

interface FeedbackStripProps {
  /** The ai_request_id from the answer API response */
  aiRequestId: string | null;
  /** Optional callback when feedback is submitted */
  onFeedbackSubmitted?: (rating: number) => void;
}

const FEEDBACK_TAGS = [
  { id: 'missed_context', label: 'Missed context' },
  { id: 'wrong_facts', label: 'Wrong facts' },
  { id: 'too_verbose', label: 'Too verbose' },
  { id: 'citations_off', label: 'Citations off' },
  { id: 'formatting', label: 'UI/formatting' },
  { id: 'other', label: 'Other' },
];

export function FeedbackStrip({ aiRequestId, onFeedbackSubmitted }: FeedbackStripProps) {
  const [submitted, setSubmitted] = useState<'positive' | 'negative' | null>(null);
  const [showDetailPanel, setShowDetailPanel] = useState(false);
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [comment, setComment] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submitFeedback = async (rating: number, tags?: string[], feedbackComment?: string) => {
    if (!aiRequestId) {
      console.warn('FeedbackStrip: No aiRequestId provided');
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const response = await apiFetch('/api/feedback', {
        method: 'POST',
        body: JSON.stringify({
          target_type: 'answer',
          target_id: aiRequestId,
          rating,
          tags: tags || undefined,
          comment: feedbackComment || undefined,
        }),
      });

      if (!response.ok) {
        // Try to get error detail from response
        const errorData = await response.json().catch(() => null);
        const errorMsg = errorData?.detail || `Server error (${response.status})`;
        throw new Error(errorMsg);
      }

      // Verify we got a success response
      const data = await response.json().catch(() => ({ success: true }));
      if (data.success === false) {
        throw new Error(data.message || 'Feedback submission failed');
      }

      setSubmitted(rating === 1 ? 'positive' : 'negative');
      setShowDetailPanel(false);
      onFeedbackSubmitted?.(rating);
    } catch (err) {
      console.error('Feedback submission error:', err);
      const message = err instanceof Error ? err.message : 'Failed to submit';
      setError(message.length > 100 ? 'Failed to submit. Please try again.' : message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleThumbsUp = () => {
    submitFeedback(1);
  };

  const handleThumbsDown = () => {
    setShowDetailPanel(true);
  };

  const handleDetailSubmit = () => {
    submitFeedback(-1, selectedTags, comment);
  };

  const toggleTag = (tagId: string) => {
    setSelectedTags(prev =>
      prev.includes(tagId)
        ? prev.filter(t => t !== tagId)
        : [...prev, tagId]
    );
  };

  // Don't render if no aiRequestId
  if (!aiRequestId) {
    return null;
  }

  // Already submitted
  if (submitted) {
    return (
      <div className="feedback-strip submitted">
        <span className="feedback-thanks">
          {submitted === 'positive' ? '👍' : '👎'} Thanks for your feedback!
        </span>
        <style jsx>{`
          .feedback-strip.submitted {
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 12px 16px;
            background: var(--color-border-light, #1a1a1a);
            border: 1px solid var(--color-border, #262626);
            border-radius: 10px;
            margin-top: 16px;
          }
          .feedback-thanks {
            font-size: 13px;
            color: var(--color-text-muted, #737373);
            font-weight: 500;
          }
        `}</style>
      </div>
    );
  }

  return (
    <div className="feedback-strip">
      <div className="feedback-row">
        <span className="feedback-label">Was this helpful?</span>
        <div className="feedback-buttons">
          <button
            className="feedback-btn positive"
            onClick={handleThumbsUp}
            disabled={submitting}
            title="Yes, this was helpful"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14 9V5a3 3 0 0 0-3-3l-4 9v11h11.28a2 2 0 0 0 2-1.7l1.38-9a2 2 0 0 0-2-2.3zM7 22H4a2 2 0 0 1-2-2v-7a2 2 0 0 1 2-2h3" />
            </svg>
          </button>
          <button
            className={`feedback-btn negative ${showDetailPanel ? 'active' : ''}`}
            onClick={handleThumbsDown}
            disabled={submitting}
            title="No, needs improvement"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M10 15v4a3 3 0 0 0 3 3l4-9V2H5.72a2 2 0 0 0-2 1.7l-1.38 9a2 2 0 0 0 2 2.3zm7-13h2.67A2.31 2.31 0 0 1 22 4v7a2.31 2.31 0 0 1-2.33 2H17" />
            </svg>
          </button>
        </div>
      </div>

      {showDetailPanel && (
        <div className="feedback-detail-panel">
          <div className="feedback-tags">
            {FEEDBACK_TAGS.map(tag => (
              <button
                key={tag.id}
                className={`feedback-tag ${selectedTags.includes(tag.id) ? 'selected' : ''}`}
                onClick={() => toggleTag(tag.id)}
                type="button"
              >
                {tag.label}
              </button>
            ))}
          </div>
          <textarea
            className="feedback-comment"
            placeholder="Anything specific we should fix? (optional)"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            maxLength={500}
            rows={2}
          />
          <div className="feedback-actions">
            <button
              className="feedback-cancel"
              onClick={() => setShowDetailPanel(false)}
              type="button"
            >
              Cancel
            </button>
            <button
              className="feedback-submit"
              onClick={handleDetailSubmit}
              disabled={submitting}
              type="button"
            >
              {submitting ? 'Submitting...' : 'Submit Feedback'}
            </button>
          </div>
          {error && <p className="feedback-error">{error}</p>}
        </div>
      )}

      <style jsx>{`
        .feedback-strip {
          margin-top: 16px;
          padding-top: 16px;
          border-top: 1px solid var(--color-border, #262626);
        }

        .feedback-row {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 12px;
        }

        .feedback-label {
          font-size: 13px;
          color: var(--color-text-muted, #737373);
          font-weight: 500;
        }

        .feedback-buttons {
          display: flex;
          gap: 8px;
        }

        .feedback-btn {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 36px;
          height: 36px;
          border-radius: 8px;
          border: 1px solid var(--color-border, #262626);
          background: var(--color-border-light, #1a1a1a);
          color: var(--color-text-muted, #737373);
          cursor: pointer;
          transition: all 0.15s ease;
        }

        .feedback-btn:hover:not(:disabled) {
          border-color: var(--color-text-muted, #525252);
          color: var(--color-text-light, #a3a3a3);
        }

        .feedback-btn.positive:hover:not(:disabled) {
          background: rgba(34, 197, 94, 0.1);
          border-color: rgba(34, 197, 94, 0.3);
          color: #22c55e;
        }

        .feedback-btn.negative:hover:not(:disabled),
        .feedback-btn.negative.active {
          background: rgba(239, 68, 68, 0.1);
          border-color: rgba(239, 68, 68, 0.3);
          color: #ef4444;
        }

        .feedback-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .feedback-detail-panel {
          margin-top: 12px;
          padding: 16px;
          background: var(--color-border-light, #1a1a1a);
          border: 1px solid var(--color-border, #262626);
          border-radius: 10px;
        }

        .feedback-tags {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          margin-bottom: 12px;
        }

        .feedback-tag {
          padding: 6px 12px;
          font-size: 12px;
          font-weight: 500;
          border-radius: 16px;
          border: 1px solid var(--color-border, #333);
          background: transparent;
          color: var(--color-text-muted, #737373);
          cursor: pointer;
          transition: all 0.15s ease;
        }

        .feedback-tag:hover {
          border-color: var(--color-text-muted, #525252);
          color: var(--color-text-light, #a3a3a3);
        }

        .feedback-tag.selected {
          background: var(--color-text-muted, #404040);
          border-color: var(--color-text-muted, #525252);
          color: var(--color-text, #fafafa);
        }

        .feedback-comment {
          width: 100%;
          padding: 10px 12px;
          font-size: 13px;
          font-family: inherit;
          border: 1px solid var(--color-border, #333);
          border-radius: 8px;
          background: var(--color-card, #171717);
          color: var(--color-text-light, #d4d4d4);
          resize: vertical;
          min-height: 60px;
        }

        .feedback-comment::placeholder {
          color: var(--color-text-muted, #525252);
        }

        .feedback-comment:focus {
          outline: none;
          border-color: var(--color-text-muted, #525252);
        }

        .feedback-actions {
          display: flex;
          justify-content: flex-end;
          gap: 8px;
          margin-top: 12px;
        }

        .feedback-cancel {
          padding: 8px 16px;
          font-size: 13px;
          font-weight: 500;
          border-radius: 6px;
          border: 1px solid var(--color-border, #333);
          background: transparent;
          color: var(--color-text-muted, #737373);
          cursor: pointer;
          transition: all 0.15s ease;
        }

        .feedback-cancel:hover {
          border-color: var(--color-text-muted, #525252);
          color: var(--color-text-light, #a3a3a3);
        }

        .feedback-submit {
          padding: 8px 16px;
          font-size: 13px;
          font-weight: 600;
          border-radius: 6px;
          border: none;
          background: var(--color-text-muted, #525252);
          color: var(--color-text, #fafafa);
          cursor: pointer;
          transition: all 0.15s ease;
        }

        .feedback-submit:hover:not(:disabled) {
          background: var(--color-text-light, #737373);
        }

        .feedback-submit:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .feedback-error {
          margin: 8px 0 0;
          font-size: 12px;
          color: #ef4444;
        }

        @media (max-width: 480px) {
          .feedback-row {
            flex-direction: column;
            align-items: flex-start;
            gap: 8px;
          }

          .feedback-tags {
            gap: 6px;
          }

          .feedback-tag {
            padding: 5px 10px;
            font-size: 11px;
          }
        }
      `}</style>
    </div>
  );
}

export default FeedbackStrip;
