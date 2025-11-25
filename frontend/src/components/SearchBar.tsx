import React, { useState, useRef, useEffect } from 'react';

interface SearchBarProps {
  query: string;
  setQuery: (query: string) => void;
  handleSearch: (e: React.FormEvent) => void;
  loading: boolean;
  answerStyle: 'concise' | 'detailed';
  onAnswerStyleChange: (style: 'concise' | 'detailed') => void;
}

export const SearchBar: React.FC<SearchBarProps> = ({ query, setQuery, handleSearch, loading, answerStyle, onAnswerStyleChange }) => {
  const [isFocused, setIsFocused] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  
  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      handleSearch(e);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setQuery(value);
  };
  
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      setQuery('');
      inputRef.current?.blur();
    }
  };
  
  // Focus input on page load
  useEffect(() => {
    if (inputRef.current && !query) {
      inputRef.current.focus();
    }
  }, []);

  return (
    <form onSubmit={onSubmit} className="search-form">
      <div className={`search-container ${isFocused ? 'focused' : ''}`}>
        <div className="search-icon">
          {loading ? (
            <div className="spinner"></div>
          ) : (
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M21 21L16.65 16.65M19 11C19 15.4183 15.4183 19 11 19C6.58172 19 3 15.4183 3 11C3 6.58172 6.58172 3 11 3C15.4183 3 19 6.58172 19 11Z" 
                stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          )}
        </div>
        <input
          ref={inputRef}
          type="text"
          className="search-input"
          placeholder="Ask your question..."
          value={query}
          onChange={handleInputChange}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          onKeyDown={handleKeyDown}
          aria-label="Search query"
          disabled={loading}
        />
        {query && (
          <button 
            type="button" 
            className="clear-button"
            onClick={() => setQuery('')}
            aria-label="Clear search"
            tabIndex={0}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M18 6L6 18M6 6L18 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>
        )}
        <button 
          type="submit" 
          className="search-button"
          disabled={loading || !query.trim()}
          aria-label="Search"
        >
          {loading ? 'Searching...' : 'Search'}
        </button>
      </div>
      
      {/* Answer Style Toggle - Below search bar */}
      <div className="answer-style-toggle">
        <span className="toggle-label">Answer style:</span>
        <div className="toggle-buttons">
          <button
            type="button"
            className={`toggle-btn ${answerStyle === 'concise' ? 'active' : ''}`}
            onClick={() => onAnswerStyleChange('concise')}
            title="Short, focused answer (~30 seconds)"
          >
            Short
          </button>
          <button
            type="button"
            className={`toggle-btn ${answerStyle === 'detailed' ? 'active' : ''}`}
            onClick={() => onAnswerStyleChange('detailed')}
            title="Comprehensive answer (~60 seconds)"
          >
            Long
          </button>
        </div>
      </div>
      
      <style jsx>{`
        .search-container {
          position: relative;
        }
        
        .search-container.focused {
          transform: translateY(-2px);
        }
        
        .search-icon {
          position: absolute;
          left: var(--space-4);
          top: 50%;
          transform: translateY(-50%);
          color: var(--color-text-light);
          display: flex;
          align-items: center;
          justify-content: center;
          width: 24px;
          height: 24px;
          z-index: 2;
        }
        
        .search-input {
          padding-left: calc(var(--space-4) + 28px);
        }
        
        .clear-button {
          position: absolute;
          right: 140px;
          top: 50%;
          transform: translateY(-50%);
          background: none;
          border: none;
          color: var(--color-text-light);
          cursor: pointer;
          padding: var(--space-1);
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all var(--transition-fast);
        }
        
        .clear-button:hover {
          background: rgba(0, 0, 0, 0.05);
          color: var(--color-text);
        }
        
        .spinner {
          width: 20px;
          height: 20px;
          border: 2px solid rgba(59, 130, 246, 0.3);
          border-radius: 50%;
          border-top-color: var(--color-primary);
          animation: spin 0.8s linear infinite;
        }
        
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
        
        .answer-style-toggle {
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 12px;
          margin-top: 16px;
        }

        .toggle-label {
          font-size: 14px;
          font-weight: 500;
          color: #6b7280;
        }

        .toggle-buttons {
          display: inline-flex;
          background: var(--color-border, #e5e7eb);
          padding: 3px;
          border-radius: 12px;
          gap: 3px;
          box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.06);
        }

        .toggle-btn {
          padding: 10px 28px;
          font-size: 14px;
          font-weight: 600;
          color: var(--color-text-light, #6b7280);
          background: transparent;
          border: none;
          border-radius: 10px;
          cursor: pointer;
          transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
          white-space: nowrap;
          position: relative;
        }

        .toggle-btn:hover:not(.active) {
          color: var(--color-text, #1f2937);
          background: rgba(255, 255, 255, 0.5);
        }

        .toggle-btn.active {
          background: var(--color-card, #ffffff);
          color: var(--color-text, #000000);
          box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1), 0 1px 2px rgba(0, 0, 0, 0.06);
        }
        
        @media (max-width: 768px) {
          .search-icon {
            left: var(--space-3);
          }

          .search-input {
            padding-left: calc(var(--space-3) + 28px);
            padding-right: var(--space-3);
            font-size: 1rem;
          }

          .clear-button {
            right: var(--space-3);
            padding: var(--space-2);
          }
          
          .search-button {
            margin-top: var(--space-3);
            font-size: 1rem;
            padding: var(--space-3) var(--space-5);
          }
          
          .answer-style-toggle {
            flex-direction: column;
            gap: 8px;
            margin-top: 12px;
          }

          .toggle-buttons {
            width: 100%;
            max-width: 300px;
          }

          .toggle-btn {
            flex: 1;
          }
        }

        @media (max-width: 480px) {
          .search-icon {
            width: 20px;
            height: 20px;
          }

          .search-icon svg {
            width: 18px;
            height: 18px;
          }

          .search-input {
            font-size: 0.95rem;
            padding: var(--space-3) var(--space-3) var(--space-3) calc(var(--space-3) + 24px);
          }

          .search-input::placeholder {
            font-size: 0.9rem;
          }

          .clear-button svg {
            width: 14px;
            height: 14px;
          }

          .search-button {
            font-size: 0.95rem;
            padding: var(--space-3) var(--space-4);
          }

          .spinner {
            width: 18px;
            height: 18px;
          }
        }
      `}</style>
    </form>
  );
};
