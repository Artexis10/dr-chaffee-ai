import { useState, useEffect } from 'react';

interface Citation {
  video_id: string;
  title: string;
  t_start_s: number;
  published_at: string;
}


interface AnswerData {
  answer_md: string;
  citations: Citation[];
  confidence: number;
  notes?: string;
  used_chunk_ids: string[];
  cached?: boolean;
  cache_date?: string;
}

interface AnswerCardProps {
  answer: AnswerData | null;
  loading: boolean;
  error?: string;
  onPlayClip?: (videoId: string, timestamp: number) => void;
  onCopyLink?: (url: string) => void;
  onCancel?: () => void;
  answerStyle?: 'concise' | 'detailed';
  onStyleChange?: (style: 'concise' | 'detailed') => void;
}

export function AnswerCard({ answer, loading, error, onPlayClip, onCopyLink, onCancel, answerStyle = 'concise', onStyleChange }: AnswerCardProps) {
  const [showSources, setShowSources] = useState(false);
  const [loadingTime, setLoadingTime] = useState(0);
  const [stats, setStats] = useState({ segments: 1695, videos: 26 }); // Default fallback values
  
  // Fetch stats on mount
  useEffect(() => {
    fetch('/api/stats')
      .then(res => res.json())
      .then(data => {
        if (data.segments && data.videos) {
          setStats({ segments: data.segments, videos: data.videos });
        }
      })
      .catch(err => {
        console.warn('Failed to fetch stats, using fallback values:', err);
      });
  }, []);
  
  // Track loading time
  useEffect(() => {
    let interval: NodeJS.Timeout;
    
    if (loading) {
      // Start the timer when loading begins
      const startTime = Date.now();
      interval = setInterval(() => {
        const elapsedSeconds = Math.floor((Date.now() - startTime) / 1000);
        setLoadingTime(elapsedSeconds);
      }, 1000);
    } else {
      // Reset timer when loading ends
      setLoadingTime(0);
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [loading]);

  if (loading) {
    // Loading messages that change based on elapsed time (using dynamic stats)
    const loadingMessages = [
      { threshold: 0, message: "Generating query embedding for semantic search..." },
      { threshold: 3, message: `Searching ${stats.segments.toLocaleString()} segments across ${stats.videos} videos...` },
      { threshold: 7, message: "Ranking segments by semantic similarity..." },
      { threshold: 12, message: "Analyzing Dr. Chaffee's transcript excerpts..." },
      { threshold: 18, message: "Synthesizing answer in Dr. Chaffee's voice..." },
      { threshold: 25, message: "Generating citations with timestamps..." },
      { threshold: 35, message: "Complex synthesis in progress..." },
      { threshold: 45, message: "Finalizing AI-emulated response..." }
    ];
    
    // Get appropriate message based on loading time
    const currentMessage = loadingMessages
      .filter(item => loadingTime >= item.threshold)
      .pop()?.message || loadingMessages[0].message;
    
    // Calculate progress percentage (capped at 90% to indicate it's still working)
    const progressPercentage = Math.min(90, loadingTime * 2);
    
    return (
      <div className="modern-answer-card loading">
        <div className="loading-header">
          <div className="loading-avatar">
            <div className="spinner"></div>
          </div>
          <div className="loading-text">
            <h3>Emulated Dr. Chaffee (AI)</h3>
            <p>{currentMessage}</p>
            <div className="loading-timer">{loadingTime}s</div>
          </div>
        </div>
        <div className="loading-progress">
          <div className="progress-bar" style={{ width: `${progressPercentage}%`, animation: 'none' }}></div>
        </div>
        <div className="loading-tips">
          <p>While you wait:</p>
          <ul>
            <li>Generating embeddings for semantic search across {stats.segments.toLocaleString()} segments</li>
            <li>AI is analyzing Dr. Chaffee's transcript content from {stats.videos} videos</li>
            <li>Synthesizing answer in Dr. Chaffee's voice with citations</li>
          </ul>
        </div>
        
        {/* Show cancel button after 15 seconds */}
        {loadingTime >= 15 && onCancel && (
          <div className="loading-actions">
            <button onClick={onCancel} className="cancel-button">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M6 18L18 6M6 6l12 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              Cancel and show search results
            </button>
          </div>
        )}
        <style jsx>{`
          .modern-answer-card {
            background: #ffffff;
            border: 1px solid #e5e7eb;
            border-radius: 16px;
            padding: 32px;
            margin-bottom: 32px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            transition: all 0.3s ease;
          }
          .loading-header {
            display: flex;
            align-items: center;
            gap: 16px;
            margin-bottom: 24px;
          }
          .loading-avatar {
            width: 48px;
            height: 48px;
            border-radius: 12px;
            background: linear-gradient(135deg, #3b82f6, #1d4ed8);
            display: flex;
            align-items: center;
            justify-content: center;
            position: relative;
          }
          .spinner {
            width: 24px;
            height: 24px;
            border: 2px solid rgba(255, 255, 255, 0.3);
            border-top: 2px solid white;
            border-radius: 50%;
            animation: spin 1s linear infinite;
          }
          .loading-text h3 {
            margin: 0 0 4px 0;
            font-size: 18px;
            font-weight: 600;
            color: #111827;
          }
          .loading-text p {
            margin: 0;
            font-size: 14px;
            color: #6b7280;
            line-height: 1.4;
          }
          .loading-timer {
            display: inline-block;
            background: rgba(59, 130, 246, 0.1);
            color: #3b82f6;
            font-size: 12px;
            font-weight: 600;
            padding: 2px 8px;
            border-radius: 12px;
            margin-top: 8px;
          }
          .loading-progress {
            height: 4px;
            background: #f3f4f6;
            border-radius: 2px;
            overflow: hidden;
            margin-bottom: 24px;
          }
          .progress-bar {
            height: 100%;
            background: linear-gradient(90deg, #3b82f6, #1d4ed8);
            border-radius: 2px;
            transition: width 0.5s ease;
          }
          .loading-tips {
            background: rgba(59, 130, 246, 0.05);
            border: 1px solid rgba(59, 130, 246, 0.1);
            border-radius: 12px;
            padding: 16px;
            margin-top: 24px;
          }
          .loading-tips p {
            margin: 0 0 8px 0;
            font-weight: 600;
            color: #4b5563;
          }
          .loading-tips ul {
            margin: 0;
            padding-left: 20px;
          }
          .loading-tips li {
            margin-bottom: 6px;
            font-size: 14px;
            color: #6b7280;
          }
          .loading-tips li:last-child {
            margin-bottom: 0;
          }
          .loading-actions {
            display: flex;
            justify-content: center;
            margin-top: 24px;
          }
          .cancel-button {
            display: flex;
            align-items: center;
            gap: 8px;
            background: transparent;
            border: 1px solid #e5e7eb;
            color: #6b7280;
            font-size: 14px;
            font-weight: 500;
            padding: 8px 16px;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.2s ease;
          }
          .cancel-button:hover {
            background: #f9fafb;
            border-color: #d1d5db;
            color: #4b5563;
          }
          .cancel-button svg {
            color: #9ca3af;
          }
          @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
          }
          @keyframes loading-progress {
            0% { width: 0%; transform: translateX(-100%); }
            50% { width: 100%; transform: translateX(0%); }
            100% { width: 0%; transform: translateX(100%); }
          }
        `}</style>
      </div>
    );
  }

  if (error) {
    return (
      <div className="modern-answer-card error">
        <div className="error-header">
          <div className="error-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="#ef4444" strokeWidth="2"/>
              <path d="m15 9-6 6" stroke="#ef4444" strokeWidth="2"/>
              <path d="m9 9 6 6" stroke="#ef4444" strokeWidth="2"/>
            </svg>
          </div>
          <div className="error-title">
            <h3>Unable to Generate Answer</h3>
          </div>
        </div>
        
        <div className="error-content">
          <div className="error-message">
            <p>{error}</p>
            
            {error.toLowerCase().includes('rate limit') && (
              <div className="error-tips">
                <h4>Why this happens:</h4>
                <ul>
                  <li>Our AI service has usage limits to ensure fair access for all users</li>
                  <li>The system will automatically retry your request</li>
                  <li>If you see this message repeatedly, please wait a few minutes before trying again</li>
                </ul>
              </div>
            )}
          </div>
          
          <div className="error-actions">
            <button className="retry-button" onClick={() => window.location.reload()}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <path d="M21 12C21 16.9706 16.9706 21 12 21C7.02944 21 3 16.9706 3 12C3 7.02944 7.02944 3 12 3" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                <path d="M12 3C13.5 3 16.5 4 16.5 8" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                <path d="M21 3L17 7M21 3V7M21 3H17" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              Refresh Page
            </button>
          </div>
        </div>
        
        <style jsx>{`
          .modern-answer-card.error {
            background: var(--color-error, #fef2f2);
            border: 1px solid var(--color-border, #fecaca);
            border-radius: var(--radius-xl, 16px);
            padding: 24px;
            margin-bottom: 32px;
            animation: pulse 2s infinite;
          }
          
          @keyframes pulse {
            0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.2); }
            70% { box-shadow: 0 0 0 6px rgba(239, 68, 68, 0); }
            100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
          }
          
          .error-header {
            display: flex;
            align-items: center;
            gap: 16px;
            margin-bottom: 16px;
            padding-bottom: 16px;
            border-bottom: 1px solid var(--color-border, #fecaca);
          }
          
          .error-icon {
            flex-shrink: 0;
            width: 48px;
            height: 48px;
            border-radius: var(--radius-lg, 12px);
            background: rgba(239, 68, 68, 0.2);
            display: flex;
            align-items: center;
            justify-content: center;
          }
          
          .error-title h3 {
            margin: 0;
            font-size: 18px;
            font-weight: 600;
            color: var(--color-error, #dc2626);
          }
          
          .error-content {
            display: flex;
            flex-direction: column;
            gap: 20px;
          }
          
          .error-message p {
            margin: 0 0 16px 0;
            font-size: 16px;
            color: var(--color-text, #7f1d1d);
            line-height: 1.5;
            font-weight: 500;
          }
          
          .error-tips {
            background: var(--color-card, #fff);
            border: 1px solid var(--color-border, #fecaca);
            border-radius: var(--radius-lg, 12px);
            padding: 16px;
            margin-top: 16px;
          }
          
          .error-tips h4 {
            margin: 0 0 12px 0;
            font-size: 14px;
            font-weight: 600;
            color: var(--color-error, #dc2626);
          }
          
          .error-tips ul {
            margin: 0;
            padding-left: 20px;
          }
          
          .error-tips li {
            margin-bottom: 8px;
            font-size: 14px;
            color: var(--color-text, #7f1d1d);
          }
          
          .error-actions {
            display: flex;
            justify-content: flex-end;
            margin-top: 8px;
          }
          
          .retry-button {
            display: flex;
            align-items: center;
            gap: 8px;
            background: var(--color-error, #dc2626);
            color: white;
            border: none;
            border-radius: var(--radius-md, 8px);
            padding: 10px 16px;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            transition: all var(--transition-normal, 0.2s ease);
          }
          
          .retry-button:hover {
            background: #b91c1c;
            transform: translateY(-1px);
          }
          
          @media (max-width: 640px) {
            .error-header {
              flex-direction: column;
              align-items: flex-start;
              gap: 12px;
            }
            
            .error-actions {
              justify-content: center;
            }
          }
        `}</style>
      </div>
    );
  }

  if (!answer) {
    return null;
  }

  // Parse inline citations and convert to clickable chips
  const renderAnswerWithCitations = (text: string) => {
    const citationRegex = /\[([^@]+)@(\d+:\d+)\]/g;
    const parts = [];
    let lastIndex = 0;
    let match;
    const seenCitations = new Set<string>(); // Track seen citations to avoid duplicates

    while ((match = citationRegex.exec(text)) !== null) {
      // Add text before citation
      if (match.index > lastIndex) {
        parts.push(text.substring(lastIndex, match.index));
      }

      // Find corresponding citation data
      const videoId = match[1];
      const timestamp = match[2];
      const citationKey = `${videoId}@${timestamp}`;
      
      // Skip if we've already seen this exact citation
      if (seenCitations.has(citationKey)) {
        lastIndex = match.index + match[0].length;
        continue;
      }
      
      seenCitations.add(citationKey);
      
      const citation = answer.citations.find(c => 
        c.video_id === videoId && formatTimestamp(c.t_start_s) === timestamp
      );

      if (citation) {
        parts.push(
          <button
            key={match.index}
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              console.log('Citation clicked:', videoId, 'at', citation.t_start_s, 'seconds');
              console.log('onPlayClip function:', onPlayClip);
              
              if (onPlayClip) {
                console.log(`🎥 Calling onPlayClip with videoId=${videoId}, timestamp=${citation.t_start_s}`);
                onPlayClip(videoId, citation.t_start_s);
              } else {
                console.warn('⚠️ onPlayClip not available, opening YouTube');
                window.open(`https://www.youtube.com/watch?v=${videoId}&t=${Math.floor(citation.t_start_s)}s`, '_blank');
              }
            }}
            title={`Click to play at ${timestamp}`}
            type="button"
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '3px',
              padding: '2px 8px',
              background: 'linear-gradient(135deg, #dbeafe, #bfdbfe)',
              color: '#1e40af',
              borderRadius: '10px',
              fontSize: '0.75em',
              fontWeight: 600,
              fontFamily: "'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', monospace",
              cursor: 'pointer',
              transition: 'all 0.2s ease',
              textDecoration: 'none',
              userSelect: 'none',
              border: 'none',
              whiteSpace: 'nowrap',
              margin: '0 2px',
              position: 'relative',
              top: '-1px'
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'linear-gradient(135deg, #bfdbfe, #93c5fd)';
              e.currentTarget.style.transform = 'translateY(-1px)';
              e.currentTarget.style.boxShadow = '0 2px 6px rgba(59, 130, 246, 0.2)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'linear-gradient(135deg, #dbeafe, #bfdbfe)';
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.boxShadow = 'none';
            }}
          >
            {timestamp}
          </button>
        );
      } else {
        parts.push(`[${match[1]}@${match[2]}]`);
      }

      lastIndex = match.index + match[0].length;
    }

    // Add remaining text
    if (lastIndex < text.length) {
      parts.push(text.substring(lastIndex));
    }

    return parts;
  };

  const formatTimestamp = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  };

  const formatDate = (dateString: string): string => {
    if (!dateString || dateString === '1970-01-01') return 'Date unavailable';
    const date = new Date(dateString);
    // Check if date is valid and not Unix epoch
    if (isNaN(date.getTime()) || date.getFullYear() === 1970) {
      return 'Date unavailable';
    }
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const confidenceColor = answer.confidence >= 0.8 
    ? '#10b981' 
    : answer.confidence >= 0.6 
    ? '#f59e0b' 
    : '#ef4444';

  const confidenceLabel = answer.confidence >= 0.8
    ? 'High'
    : answer.confidence >= 0.6
    ? 'Medium'
    : 'Low';

  return (
    <div className="modern-answer-card">
      <div className="answer-header">
        <div className="doctor-avatar">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <path d="M12 2C13.1 2 14 2.9 14 4C14 5.1 13.1 6 12 6C10.9 6 10 5.1 10 4C10 2.9 10.9 2 12 2ZM21 9V7L15 4V6L13.5 7V9H21ZM3 9V7L9 4V6L10.5 7V9H3ZM12 7.5C12.8 7.5 13.5 8.2 13.5 9S12.8 10.5 12 10.5 10.5 9.8 10.5 9 11.2 7.5 12 7.5Z" fill="#3b82f6"/>
          </svg>
        </div>
        <div className="header-content">
          <div className="title-row">
            <div className="title-with-badge">
              <h3>Dr. Chaffee's Answer</h3>
              <span className="ai-badge" title="AI-generated response based on Dr. Chaffee's video content">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
                  <path d="M12 2L2 7L12 12L22 7L12 2Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  <path d="M2 17L12 22L22 17" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  <path d="M2 12L12 17L22 12" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
                AI Emulated
              </span>
            </div>
            <div className="badges">
              {onStyleChange && (
                <div className="answer-style-toggle">
                  <button
                    className={`style-button ${answerStyle === 'concise' ? 'active' : ''}`}
                    onClick={() => onStyleChange('concise')}
                    title="Short, concise answer"
                  >
                    Short
                  </button>
                  <button
                    className={`style-button ${answerStyle === 'detailed' ? 'active' : ''}`}
                    onClick={() => onStyleChange('detailed')}
                    title="Detailed, comprehensive answer"
                  >
                    Long
                  </button>
                </div>
              )}
              <span 
                className="confidence-badge"
                style={{ backgroundColor: confidenceColor }}
              >
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
                  <path d="M9 12L11 14L15 10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2"/>
                </svg>
                {confidenceLabel}
              </span>
              {answer.cached && (
                <span className="cache-badge" title={`Cached on ${formatDate(answer.cache_date!)}`}>
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" stroke="currentColor" strokeWidth="2"/>
                    <polyline points="14,2 14,8 20,8" stroke="currentColor" strokeWidth="2"/>
                  </svg>
                  Cached
                </span>
              )}
            </div>
          </div>
          <p className="subtitle">Based on verified transcript content</p>
        </div>
      </div>

      <div className="answer-content">
        <div className="answer-text">
          {renderAnswerWithCitations(answer.answer_md)}
        </div>

        {answer.notes && (
          <div className="answer-notes">
            <div className="note-icon">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <circle cx="12" cy="12" r="10" stroke="#6b7280" strokeWidth="2"/>
                <path d="M12 6v6l4 2" stroke="#6b7280" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </div>
            <p>{answer.notes}</p>
          </div>
        )}
      </div>


      <div className="answer-footer">
        <button 
          className="sources-toggle" 
          onClick={() => setShowSources(!showSources)}
        >
          <div className="toggle-content">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
              <path d="M9 11H15M9 15H15M17 21L19.2929 18.7071C19.6834 18.3166 19.8787 18.1213 19.8787 17.8787C19.8787 17.6361 19.6834 17.4408 19.2929 17.0503L17 14.7574V21Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              <path d="M8 21H16.2C17.8802 21 18.7202 21 19.362 20.673C19.9265 20.3854 20.3854 19.9265 20.673 19.362C21 18.7202 21 17.8802 21 16.2V7.8C21 6.11984 21 5.27976 20.673 4.63803C20.3854 4.07354 19.9265 3.6146 19.362 3.32698C18.7202 3 17.8802 3 16.2 3H7.8C6.11984 3 5.27976 3 4.63803 3.32698C4.07354 3.6146 3.6146 4.07354 3.32698 4.63803C3 5.27976 3 6.11984 3 7.8V16.2C3 17.8802 3 18.7202 3.32698 19.362C3.6146 19.9265 4.07354 20.3854 4.63803 20.673C5.27976 21 6.11984 21 7.8 21H8Z" stroke="currentColor" strokeWidth="2"/>
            </svg>
            <span>Citation Details</span>
            <span className="citation-count">({answer.citations.length})</span>
          </div>
          <svg 
            width="16" 
            height="16" 
            viewBox="0 0 24 24" 
            fill="none"
            className={`toggle-arrow ${showSources ? 'expanded' : ''}`}
          >
            <path d="M6 9L12 15L18 9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        </button>
        
        {showSources && (
          <div className="sources-list">
            {answer.citations.map((citation, index) => (
              <div key={index} className="source-item">
                <div className="source-info">
                  <button
                    className="play-button"
                    onClick={() => onPlayClip && onPlayClip(citation.video_id, citation.t_start_s)}
                    title="Play this clip"
                  >
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                      <path d="M8 5V19L19 12L8 5Z" fill="currentColor"/>
                    </svg>
                  </button>
                  <div className="source-details">
                    <div className="source-title">
                      {citation.title}
                    </div>
                    <div className="source-meta">
                      <span className="source-timestamp">
                        {formatTimestamp(citation.t_start_s)}
                      </span>
                      <span className="source-date">
                        {formatDate(citation.published_at)}
                      </span>
                    </div>
                  </div>
                </div>
                <button
                  className="copy-link-button"
                  onClick={() => {
                    const url = `https://youtube.com/watch?v=${citation.video_id}&t=${Math.floor(citation.t_start_s)}s`;
                    onCopyLink && onCopyLink(url);
                  }}
                  title="Copy YouTube link"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                    <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                    <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <style jsx>{`
        .modern-answer-card {
          background: #ffffff;
          border: 1px solid #e5e7eb;
          border-radius: 16px;
          padding: 32px;
          margin-bottom: 32px;
          box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
          transition: all 0.3s ease;
        }

        .modern-answer-card:hover {
          box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
          transform: translateY(-1px);
        }

        .answer-header {
          display: flex;
          align-items: flex-start;
          gap: 16px;
          margin-bottom: 24px;
        }

        .doctor-avatar {
          width: 48px;
          height: 48px;
          border-radius: 12px;
          background: linear-gradient(135deg, #dbeafe, #bfdbfe);
          display: flex;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;
        }

        .header-content {
          flex: 1;
          min-width: 0;
        }

        .title-row {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          gap: 16px;
          margin-bottom: 4px;
        }

        .title-with-badge {
          display: flex;
          align-items: center;
          gap: 10px;
        }

        .title-row h3 {
          margin: 0;
          font-size: 20px;
          font-weight: 700;
          color: #111827;
          line-height: 1.3;
        }

        .ai-badge {
          display: inline-flex;
          align-items: center;
          gap: 4px;
          padding: 4px 10px;
          background: linear-gradient(135deg, #f3e8ff, #e9d5ff);
          color: #7c3aed;
          border-radius: 12px;
          font-size: 11px;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          cursor: help;
          transition: all 0.2s ease;
        }

        .ai-badge:hover {
          background: linear-gradient(135deg, #e9d5ff, #ddd6fe);
          transform: scale(1.05);
        }

        .ai-badge svg {
          flex-shrink: 0;
        }

        .subtitle {
          margin: 0;
          font-size: 14px;
          color: #6b7280;
          font-weight: 500;
        }

        .badges {
          display: flex;
          gap: 8px;
          align-items: center;
          flex-shrink: 0;
        }

        .answer-style-toggle {
          display: flex;
          background: #f3f4f6;
          border-radius: 8px;
          padding: 2px;
          gap: 2px;
        }

        .style-button {
          padding: 6px 14px;
          border: none;
          background: transparent;
          color: #6b7280;
          font-size: 13px;
          font-weight: 600;
          border-radius: 6px;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .style-button:hover {
          background: #e5e7eb;
          color: #374151;
        }

        .style-button.active {
          background: #ffffff;
          color: #3b82f6;
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
        }

        .confidence-badge {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 6px 12px;
          border-radius: 20px;
          font-size: 12px;
          font-weight: 600;
          color: white;
          text-transform: uppercase;
          letter-spacing: 0.05em;
        }

        .cache-badge {
          display: flex;
          align-items: center;
          gap: 6px;
          padding: 6px 12px;
          border-radius: 20px;
          font-size: 12px;
          font-weight: 500;
          background: #f3f4f6;
          color: #6b7280;
        }

        .answer-content {
          margin-bottom: 24px;
        }

        .answer-text {
          font-size: 17px;
          line-height: 1.7;
          color: #374151;
          margin: 0;
          white-space: pre-wrap; /* Preserve line breaks and spacing */
        }

        .show-more-button {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          margin-top: 12px;
          padding: 8px 16px;
          background: linear-gradient(135deg, #f0f9ff, #e0f2fe);
          color: #0369a1;
          border: 1px solid #7dd3fc;
          border-radius: 8px;
          font-size: 14px;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.2s ease;
        }

        .show-more-button:hover {
          background: linear-gradient(135deg, #e0f2fe, #bae6fd);
          border-color: #0284c7;
          transform: translateY(-1px);
          box-shadow: 0 4px 8px rgba(59, 130, 246, 0.15);
        }

        .show-more-button:active {
          transform: translateY(0);
        }

        .show-more-button svg {
          flex-shrink: 0;
        }

        .citation-chip {
          display: inline-flex !important;
          align-items: center !important;
          gap: 3px !important;
          padding: 2px 8px !important;
          background: linear-gradient(135deg, #dbeafe, #bfdbfe) !important;
          color: #1e40af !important;
          border-radius: 10px !important;
          font-size: 0.75em !important;
          font-weight: 600 !important;
          font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Roboto Mono', monospace !important;
          cursor: pointer !important;
          transition: all 0.2s ease !important;
          text-decoration: none !important;
          user-select: none !important;
          pointer-events: auto !important;
          outline: none !important;
          white-space: nowrap !important;
          margin: 0 2px !important;
          position: relative !important;
          top: -1px !important;
        }

        .citation-chip:hover {
          background: linear-gradient(135deg, #bfdbfe, #93c5fd) !important;
          color: #1e3a8a !important;
          transform: translateY(-1px) !important;
          box-shadow: 0 2px 6px rgba(59, 130, 246, 0.2) !important;
        }
        
        .citation-chip:active {
          transform: translateY(0) !important;
          box-shadow: 0 1px 3px rgba(59, 130, 246, 0.15) !important;
        }
        
        .citation-chip:focus {
          outline: 2px solid #93c5fd !important;
          outline-offset: 2px !important;
        }

        .answer-notes {
          display: flex;
          align-items: flex-start;
          gap: 12px;
          background: #f9fafb;
          border: 1px solid #e5e7eb;
          padding: 16px;
          border-radius: 12px;
          margin-top: 16px;
        }

        .note-icon {
          flex-shrink: 0;
          margin-top: 2px;
        }

        .answer-notes p {
          margin: 0;
          font-size: 14px;
          color: #6b7280;
          line-height: 1.5;
        }

        .answer-footer {
          margin-top: 24px;
          padding-top: 24px;
          border-top: 1px solid #e5e7eb;
        }

        .sources-toggle {
          display: flex;
          justify-content: space-between;
          align-items: center;
          width: 100%;
          background: #f9fafb;
          border: 1px solid #e5e7eb;
          border-radius: 12px;
          padding: 16px;
          cursor: pointer;
          font-size: 14px;
          font-weight: 600;
          color: #374151;
          transition: all 0.2s ease;
        }

        .sources-toggle:hover {
          background: #f3f4f6;
          border-color: #d1d5db;
        }

        .toggle-content {
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .citation-count {
          color: #6b7280;
          font-weight: 500;
        }

        .toggle-arrow {
          transition: transform 0.2s ease;
          color: #6b7280;
        }

        .toggle-arrow.expanded {
          transform: rotate(180deg);
        }

        .sources-list {
          margin-top: 16px;
          background: #f9fafb;
          border: 1px solid #e5e7eb;
          border-radius: 12px;
          padding: 16px;
        }

        .source-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 12px 0;
          border-bottom: 1px solid #e5e7eb;
        }

        .source-item:last-child {
          border-bottom: none;
        }

        .source-info {
          display: flex;
          align-items: center;
          gap: 16px;
        }

        .play-button {
          background: #10b981;
          color: white;
          border: none;
          border-radius: 8px;
          padding: 8px;
          cursor: pointer;
          transition: all 0.2s ease;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .play-button:hover {
          background: #059669;
          transform: translateY(-1px);
        }

        .copy-link-button {
          background: #e5e7eb;
          color: #6b7280;
          border: none;
          border-radius: 8px;
          padding: 8px;
          cursor: pointer;
          transition: all 0.2s ease;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .copy-link-button:hover {
          background: #d1d5db;
          color: #374151;
          transform: translateY(-1px);
        }

        .source-details {
          display: flex;
          flex-direction: column;
          gap: 6px;
          flex: 1;
        }

        .source-title {
          font-weight: 600;
          font-size: 14px;
          color: #111827;
          line-height: 1.4;
        }

        .source-meta {
          display: flex;
          gap: 12px;
          align-items: center;
        }

        .source-timestamp {
          font-weight: 600;
          font-family: monospace;
          font-size: 13px;
          color: #3b82f6;
        }

        .source-date {
          font-size: 12px;
          color: #6b7280;
          font-weight: 500;
        }


        @media (max-width: 768px) {
          .modern-answer-card {
            padding: 24px;
            margin-bottom: 24px;
          }

          .answer-header {
            align-items: center;
          }

          .title-row {
            flex-direction: column;
            align-items: flex-start;
            gap: 12px;
          }

          .title-row h3 {
            font-size: 18px;
          }

          .badges {
            margin-top: 8px;
          }

          .source-info {
            gap: 12px;
          }

          .source-details {
            gap: 4px;
          }

          .sources-toggle {
            padding: 14px;
          }
        }
      `}</style>
    </div>
  );
}
