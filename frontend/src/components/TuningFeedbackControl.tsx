/**
 * TuningFeedbackControl Component
 * 
 * Compact inline feedback control for tuning dashboard cards.
 * Used to rate RAG profiles, search configs, and model settings.
 */

import { useState } from 'react';
import { ThumbsUp, ThumbsDown, Wrench } from 'lucide-react';
import { apiFetch } from '@/utils/api';

interface TuningFeedbackControlProps {
  /** Stable identifier for the config being rated (e.g., profile ID, config name) */
  targetId: string;
  /** Optional label to show */
  label?: string;
  /** Compact mode - just icons, no text */
  compact?: boolean;
}

type RatingType = 'positive' | 'negative' | 'broken';

export function TuningFeedbackControl({ 
  targetId, 
  label = 'Rate this config',
  compact = false 
}: TuningFeedbackControlProps) {
  const [submitted, setSubmitted] = useState<RatingType | null>(null);
  const [selected, setSelected] = useState<RatingType | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const submitFeedback = async (rating: number, ratingType: RatingType) => {
    if (submitting) return;
    
    setSelected(ratingType);
    setSubmitting(true);
    try {
      const response = await apiFetch('/api/feedback', {
        method: 'POST',
        body: JSON.stringify({
          target_type: 'tuning_internal',
          target_id: targetId,
          rating,
          metadata: {
            config_id: targetId,
            feedback_source: 'tuning_dashboard',
          },
        }),
      });

      if (response.ok) {
        setSubmitted(ratingType);
      } else {
        setSelected(null);
      }
    } catch (err) {
      console.error('Tuning feedback error:', err);
      setSelected(null);
    } finally {
      setSubmitting(false);
    }
  };

  if (submitted) {
    return (
      <div className="tuning-feedback-control submitted">
        <span className="feedback-thanks">
          {submitted === 'positive' ? '👍' : submitted === 'negative' ? '👎' : '🛠'} Noted
        </span>
        <style jsx>{`
          .tuning-feedback-control.submitted {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 4px 8px;
            font-size: 11px;
            color: var(--text-muted, #737373);
          }
          .feedback-thanks {
            opacity: 0.8;
          }
        `}</style>
      </div>
    );
  }

  return (
    <div className="tuning-feedback-control">
      {!compact && <span className="feedback-label">{label}</span>}
      <div className="feedback-buttons">
        <button
          className={`feedback-btn good ${selected === 'positive' ? 'selected' : ''}`}
          onClick={() => submitFeedback(1, 'positive')}
          disabled={submitting}
          title="Good"
        >
          <ThumbsUp size={12} />
          {!compact && <span>Good</span>}
        </button>
        <button
          className={`feedback-btn bad ${selected === 'negative' ? 'selected' : ''}`}
          onClick={() => submitFeedback(-1, 'negative')}
          disabled={submitting}
          title="Needs work"
        >
          <ThumbsDown size={12} />
          {!compact && <span>Needs work</span>}
        </button>
        <button
          className={`feedback-btn broken ${selected === 'broken' ? 'selected' : ''}`}
          onClick={() => submitFeedback(-2, 'broken')}
          disabled={submitting}
          title="Broken"
        >
          <Wrench size={12} />
          {!compact && <span>Broken</span>}
        </button>
      </div>

      <style jsx>{`
        .tuning-feedback-control {
          display: flex;
          align-items: center;
          gap: 8px;
          margin-top: 8px;
          padding-top: 8px;
          border-top: 1px solid var(--border-subtle, #262626);
        }

        .feedback-label {
          font-size: 11px;
          color: var(--text-muted, #737373);
          white-space: nowrap;
        }

        .feedback-buttons {
          display: flex;
          gap: 4px;
        }

        .feedback-btn {
          display: inline-flex;
          align-items: center;
          gap: 4px;
          padding: 4px 8px;
          font-size: 11px;
          font-weight: 500;
          border-radius: 4px;
          border: 1px solid var(--border-subtle, #333);
          background: transparent;
          color: var(--text-muted, #737373);
          cursor: pointer;
          transition: all 0.15s ease;
        }

        .feedback-btn:hover:not(:disabled) {
          border-color: var(--text-muted, #525252);
          color: var(--text-light, #a3a3a3);
        }

        .feedback-btn.good:hover:not(:disabled),
        .feedback-btn.good.selected {
          background: rgba(34, 197, 94, 0.1);
          border-color: rgba(34, 197, 94, 0.4);
          color: #22c55e;
        }

        .feedback-btn.good.selected {
          background: rgba(34, 197, 94, 0.15);
          border-color: rgba(34, 197, 94, 0.5);
        }

        .feedback-btn.bad:hover:not(:disabled),
        .feedback-btn.bad.selected {
          background: rgba(239, 68, 68, 0.1);
          border-color: rgba(239, 68, 68, 0.4);
          color: #ef4444;
        }

        .feedback-btn.bad.selected {
          background: rgba(239, 68, 68, 0.15);
          border-color: rgba(239, 68, 68, 0.5);
        }

        .feedback-btn.broken:hover:not(:disabled),
        .feedback-btn.broken.selected {
          background: rgba(251, 191, 36, 0.1);
          border-color: rgba(251, 191, 36, 0.4);
          color: #fbbf24;
        }

        .feedback-btn.broken.selected {
          background: rgba(251, 191, 36, 0.15);
          border-color: rgba(251, 191, 36, 0.5);
        }

        .feedback-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .feedback-btn.selected:disabled {
          opacity: 1;
        }
      `}</style>
    </div>
  );
}

export default TuningFeedbackControl;
