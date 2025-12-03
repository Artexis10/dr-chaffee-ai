/**
 * GlobalFeedbackModal Component
 * 
 * Modal for submitting general feedback (bugs, feature requests, general thoughts).
 * Accessible from the main navigation.
 */

import { useState } from 'react';
import { apiFetch } from '@/utils/api';

interface GlobalFeedbackModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const CATEGORIES = [
  { id: 'bug', label: 'Bug Report', icon: '🐛' },
  { id: 'feature_request', label: 'Feature Request', icon: '💡' },
  { id: 'general', label: 'General Feedback', icon: '💬' },
];

export function GlobalFeedbackModal({ isOpen, onClose }: GlobalFeedbackModalProps) {
  const [category, setCategory] = useState<string>('general');
  const [comment, setComment] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async () => {
    if (!comment.trim()) {
      setError('Please enter your feedback');
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      // Get current route for context
      const currentRoute = typeof window !== 'undefined' ? window.location.pathname : null;

      const response = await apiFetch('/api/feedback', {
        method: 'POST',
        body: JSON.stringify({
          target_type: 'global',
          target_id: currentRoute,
          rating: null,
          tags: [category],
          comment: comment.trim(),
          metadata: {
            category,
            route: currentRoute,
            userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : null,
          },
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to submit feedback');
      }

      setSubmitted(true);
      setTimeout(() => {
        onClose();
        // Reset state after close
        setTimeout(() => {
          setSubmitted(false);
          setComment('');
          setCategory('general');
        }, 300);
      }, 1500);
    } catch (err) {
      console.error('Feedback submission error:', err);
      setError('Failed to submit. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleClose = () => {
    if (!submitting) {
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <>
      <div className="modal-overlay" onClick={handleClose} />
      <div className="modal-container">
        <div className="modal-content">
          <div className="modal-header">
            <h2>Send Feedback</h2>
            <button className="modal-close" onClick={handleClose} disabled={submitting}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M18 6L6 18M6 6l12 12" />
              </svg>
            </button>
          </div>

          {submitted ? (
            <div className="modal-success">
              <div className="success-icon">✓</div>
              <p>Thanks for your feedback!</p>
            </div>
          ) : (
            <>
              <div className="modal-body">
                <div className="category-selector">
                  {CATEGORIES.map(cat => (
                    <button
                      key={cat.id}
                      className={`category-btn ${category === cat.id ? 'selected' : ''}`}
                      onClick={() => setCategory(cat.id)}
                      type="button"
                    >
                      <span className="category-icon">{cat.icon}</span>
                      <span className="category-label">{cat.label}</span>
                    </button>
                  ))}
                </div>

                <textarea
                  className="feedback-textarea"
                  placeholder={
                    category === 'bug'
                      ? 'Describe the bug you encountered...'
                      : category === 'feature_request'
                      ? 'What feature would you like to see?'
                      : 'Share your thoughts...'
                  }
                  value={comment}
                  onChange={(e) => setComment(e.target.value)}
                  maxLength={2000}
                  rows={5}
                />

                <div className="char-count">
                  {comment.length} / 2000
                </div>

                {error && <p className="error-message">{error}</p>}
              </div>

              <div className="modal-footer">
                <button className="btn-cancel" onClick={handleClose} disabled={submitting}>
                  Cancel
                </button>
                <button
                  className="btn-submit"
                  onClick={handleSubmit}
                  disabled={submitting || !comment.trim()}
                >
                  {submitting ? 'Sending...' : 'Send Feedback'}
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      <style jsx>{`
        .modal-overlay {
          position: fixed;
          inset: 0;
          background: rgba(0, 0, 0, 0.6);
          backdrop-filter: blur(4px);
          z-index: 9998;
          animation: fadeIn 0.2s ease;
        }

        .modal-container {
          position: fixed;
          inset: 0;
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 9999;
          padding: 20px;
        }

        .modal-content {
          background: var(--color-card, #171717);
          border: 1px solid var(--color-border, #262626);
          border-radius: 16px;
          width: 100%;
          max-width: 480px;
          max-height: 90vh;
          overflow-y: auto;
          animation: slideUp 0.2s ease;
        }

        .modal-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 20px 24px;
          border-bottom: 1px solid var(--color-border, #262626);
        }

        .modal-header h2 {
          margin: 0;
          font-size: 18px;
          font-weight: 600;
          color: var(--color-text, #fafafa);
        }

        .modal-close {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 32px;
          height: 32px;
          border: none;
          border-radius: 8px;
          background: transparent;
          color: var(--color-text-muted, #737373);
          cursor: pointer;
          transition: all 0.15s ease;
        }

        .modal-close:hover:not(:disabled) {
          background: var(--color-border, #262626);
          color: var(--color-text-light, #a3a3a3);
        }

        .modal-body {
          padding: 24px;
        }

        .category-selector {
          display: flex;
          gap: 8px;
          margin-bottom: 16px;
        }

        .category-btn {
          flex: 1;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 6px;
          padding: 12px 8px;
          border: 1px solid var(--color-border, #333);
          border-radius: 10px;
          background: transparent;
          cursor: pointer;
          transition: all 0.15s ease;
        }

        .category-btn:hover {
          border-color: var(--color-text-muted, #525252);
        }

        .category-btn.selected {
          background: var(--color-border, #262626);
          border-color: var(--color-text-muted, #525252);
        }

        .category-icon {
          font-size: 20px;
        }

        .category-label {
          font-size: 11px;
          font-weight: 500;
          color: var(--color-text-muted, #737373);
        }

        .category-btn.selected .category-label {
          color: var(--color-text-light, #a3a3a3);
        }

        .feedback-textarea {
          width: 100%;
          padding: 12px 14px;
          font-size: 14px;
          font-family: inherit;
          line-height: 1.5;
          border: 1px solid var(--color-border, #333);
          border-radius: 10px;
          background: var(--color-bg, #0a0a0a);
          color: var(--color-text-light, #d4d4d4);
          resize: vertical;
          min-height: 120px;
        }

        .feedback-textarea::placeholder {
          color: var(--color-text-muted, #525252);
        }

        .feedback-textarea:focus {
          outline: none;
          border-color: var(--color-text-muted, #525252);
        }

        .char-count {
          text-align: right;
          font-size: 11px;
          color: var(--color-text-muted, #525252);
          margin-top: 6px;
        }

        .error-message {
          margin: 12px 0 0;
          font-size: 13px;
          color: #ef4444;
        }

        .modal-footer {
          display: flex;
          justify-content: flex-end;
          gap: 10px;
          padding: 16px 24px;
          border-top: 1px solid var(--color-border, #262626);
        }

        .btn-cancel {
          padding: 10px 18px;
          font-size: 14px;
          font-weight: 500;
          border-radius: 8px;
          border: 1px solid var(--color-border, #333);
          background: transparent;
          color: var(--color-text-muted, #737373);
          cursor: pointer;
          transition: all 0.15s ease;
        }

        .btn-cancel:hover:not(:disabled) {
          border-color: var(--color-text-muted, #525252);
          color: var(--color-text-light, #a3a3a3);
        }

        .btn-submit {
          padding: 10px 20px;
          font-size: 14px;
          font-weight: 600;
          border-radius: 8px;
          border: none;
          background: var(--color-text, #fafafa);
          color: var(--color-bg, #0a0a0a);
          cursor: pointer;
          transition: all 0.15s ease;
        }

        .btn-submit:hover:not(:disabled) {
          opacity: 0.9;
        }

        .btn-submit:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .modal-success {
          padding: 48px 24px;
          text-align: center;
        }

        .success-icon {
          width: 56px;
          height: 56px;
          margin: 0 auto 16px;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 28px;
          background: rgba(34, 197, 94, 0.1);
          border: 2px solid rgba(34, 197, 94, 0.3);
          border-radius: 50%;
          color: #22c55e;
        }

        .modal-success p {
          margin: 0;
          font-size: 16px;
          font-weight: 500;
          color: var(--color-text-light, #a3a3a3);
        }

        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }

        @keyframes slideUp {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        @media (max-width: 480px) {
          .modal-content {
            max-height: 85vh;
          }

          .category-selector {
            flex-direction: column;
          }

          .category-btn {
            flex-direction: row;
            justify-content: flex-start;
            padding: 12px 16px;
          }
        }
      `}</style>
    </>
  );
}

export default GlobalFeedbackModal;
