import React from 'react';

export const DisclaimerBanner: React.FC = () => {
  return (
    <>
      <div className="disclaimer-container">
        <div className="disclaimer-card">
          <div className="disclaimer-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 9V11M12 15H12.01M5.07183 19H18.9282C20.4678 19 21.4301 17.3333 20.6603 16L13.7321 4C12.9623 2.66667 11.0377 2.66667 10.2679 4L3.33975 16C2.56995 17.3333 3.53223 19 5.07183 19Z" 
                stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
          <div className="disclaimer-text">
            <strong>Educational Content Only:</strong> This AI tool provides educational information based on Anthony Chaffee's content. 
            Always consult your healthcare provider for personalized advice.
          </div>
        </div>

        <div className="patreon-card">
          <div className="patreon-icon">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2Z" 
                stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="currentColor"/>
            </svg>
          </div>
          <div className="patreon-text">
            <strong>Patreon Exclusive:</strong> This tool is an exclusive benefit for Dr. Chaffee's Patreon community members.
          </div>
        </div>
      </div>

      <style jsx>{`
        .disclaimer-container {
          display: flex;
          gap: var(--space-3);
          margin-bottom: var(--space-6);
          flex-wrap: wrap;
        }

        .disclaimer-card,
        .patreon-card {
          flex: 1;
          min-width: min(280px, 100%);
          display: flex;
          align-items: center;
          gap: var(--space-3);
          padding: var(--space-3) var(--space-4);
          border-radius: var(--radius-lg);
          font-size: 0.9rem;
          line-height: 1.5;
          transition: all var(--transition-normal);
        }

        .disclaimer-card {
          background: rgba(239, 68, 68, 0.08);
          border: 1px solid rgba(239, 68, 68, 0.2);
          color: var(--color-text);
        }

        .disclaimer-card:hover {
          background: rgba(239, 68, 68, 0.12);
          border-color: rgba(239, 68, 68, 0.3);
        }

        .patreon-card {
          background: rgba(245, 158, 11, 0.08);
          border: 1px solid rgba(245, 158, 11, 0.2);
          color: var(--color-text);
        }

        .patreon-card:hover {
          background: rgba(245, 158, 11, 0.12);
          border-color: rgba(245, 158, 11, 0.3);
        }

        .disclaimer-icon,
        .patreon-icon {
          flex-shrink: 0;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .disclaimer-icon {
          color: #ef4444;
        }

        .patreon-icon {
          color: #f59e0b;
        }

        .disclaimer-text,
        .patreon-text {
          flex: 1;
        }

        .disclaimer-text strong,
        .patreon-text strong {
          font-weight: 600;
          color: var(--color-text);
        }

        @media (max-width: 768px) {
          .disclaimer-container {
            flex-direction: column;
            gap: var(--space-2);
            margin-bottom: var(--space-4);
          }

          .disclaimer-card,
          .patreon-card {
            min-width: 100%;
            padding: var(--space-3);
            font-size: 0.875rem;
          }
        }

        @media (max-width: 480px) {
          .disclaimer-container {
            gap: 0.375rem;
          }

          .disclaimer-card,
          .patreon-card {
            padding: 0.625rem 0.75rem;
            font-size: 0.8125rem;
            gap: 0.5rem;
            border-radius: var(--radius-md);
          }

          .disclaimer-icon svg,
          .patreon-icon svg {
            width: 16px;
            height: 16px;
          }
        }

        :global(.dark-mode) .disclaimer-card {
          background: rgba(239, 68, 68, 0.12);
          border-color: rgba(239, 68, 68, 0.25);
        }

        :global(.dark-mode) .disclaimer-card:hover {
          background: rgba(239, 68, 68, 0.16);
          border-color: rgba(239, 68, 68, 0.35);
        }

        :global(.dark-mode) .patreon-card {
          background: rgba(245, 158, 11, 0.12);
          border-color: rgba(245, 158, 11, 0.25);
        }

        :global(.dark-mode) .patreon-card:hover {
          background: rgba(245, 158, 11, 0.16);
          border-color: rgba(245, 158, 11, 0.35);
        }
      `}</style>
    </>
  );
};
