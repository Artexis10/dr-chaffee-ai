/*
 * UI Theme Guardrail:
 * DO NOT modify this file unless Hugo explicitly instructs.
 * This file defines the locked-in Dr Chaffee visual system.
 * See: frontend/docs/ui-theme-guidelines.md
 */

import React, { useState, useRef, useEffect } from 'react';

interface SearchBarProps {
  query: string;
  setQuery: (query: string) => void;
  handleSearch: (e: React.FormEvent) => void;
  loading: boolean;
  answerStyle: 'concise' | 'detailed';
  onAnswerStyleChange: (style: 'concise' | 'detailed') => void;
  disabled?: boolean; // Disable all interactions while search is running
}

export const SearchBar: React.FC<SearchBarProps> = ({ query, setQuery, handleSearch, loading, answerStyle, onAnswerStyleChange, disabled = false }) => {
  const isDisabled = loading || disabled;
  const [isFocused, setIsFocused] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  
  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim() && !isDisabled) {
      handleSearch(e);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (isDisabled) return;
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
        {/* Input wrapper for proper icon/clear button positioning */}
        <div className="search-input-wrapper">
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
            className={`search-input ${isDisabled ? 'disabled' : ''}`}
            placeholder="Ask your question..."
            value={query}
            onChange={handleInputChange}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            onKeyDown={handleKeyDown}
            aria-label="Search query"
            readOnly={isDisabled}
            style={{ opacity: isDisabled ? 0.7 : 1, cursor: isDisabled ? 'not-allowed' : 'text' }}
          />
          {query && !isDisabled && (
            <button 
              type="button" 
              className="clear-button"
              onClick={() => {
                setQuery('');
                inputRef.current?.focus();
              }}
              aria-label="Clear search"
              tabIndex={0}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M18 6L6 18M6 6L18 18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </button>
          )}
        </div>
        <button 
          type="submit" 
          className="search-button"
          disabled={isDisabled || !query.trim()}
          aria-label="Search"
          style={{ opacity: isDisabled ? 0.6 : 1 }}
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
            onClick={() => !isDisabled && onAnswerStyleChange('concise')}
            title="Short, focused answer (~30 seconds)"
            disabled={isDisabled}
            style={{ opacity: isDisabled ? 0.5 : 1, cursor: isDisabled ? 'not-allowed' : 'pointer' }}
          >
            Short
          </button>
          <button
            type="button"
            className={`toggle-btn ${answerStyle === 'detailed' ? 'active' : ''}`}
            onClick={() => !isDisabled && onAnswerStyleChange('detailed')}
            title="Comprehensive answer (~60 seconds)"
            disabled={isDisabled}
            style={{ opacity: isDisabled ? 0.5 : 1, cursor: isDisabled ? 'not-allowed' : 'pointer' }}
          >
            Long
          </button>
        </div>
      </div>
      
      <style jsx>{`
        .search-form {
          max-width: 640px;
          margin: 0 auto;
          width: 100%;
          padding-top: 1.5rem; /* Space from disclaimer cards */
        }
        
        .search-container {
          position: relative;
          display: flex;
          flex-direction: column;
          gap: var(--space-4); /* Increased gap between input and button */
        }
        
        .search-container.focused .search-input-wrapper {
          transform: translateY(-1px);
        }
        
        .search-input-wrapper {
          position: relative;
          width: 100%;
          transition: transform 0.2s ease;
        }
        
        .search-icon {
          position: absolute;
          left: var(--space-4);
          top: 50%;
          transform: translateY(-50%);
          color: var(--color-text-muted);
          display: flex;
          align-items: center;
          justify-content: center;
          width: 22px;
          height: 22px;
          z-index: 2;
          pointer-events: none;
        }
        
        .search-input {
          width: 100%;
          padding: var(--space-4) var(--space-5);
          padding-left: calc(var(--space-4) + 30px);
          padding-right: 48px; /* Space for clear button */
          font-size: 1.05rem;
          border: 2px solid var(--color-border);
          border-radius: var(--radius-xl);
          background: var(--color-card);
          color: var(--color-text);
          box-shadow: var(--shadow-sm);
          transition: all 0.2s ease;
        }
        
        .search-input:focus {
          outline: none;
          border-color: var(--color-primary);
          box-shadow: 0 0 0 3px rgba(0, 0, 0, 0.08);
        }
        
        .search-input::placeholder {
          color: var(--color-text-muted);
        }
        
        .clear-button {
          position: absolute;
          right: 14px;
          top: 50%;
          transform: translateY(-50%);
          background: var(--color-border-light, #f3f4f6);
          border: 1px solid var(--color-border, #e5e7eb);
          color: var(--color-text-muted, #6b7280);
          cursor: pointer;
          padding: 6px;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: all var(--transition-fast);
          width: 28px;
          height: 28px;
        }
        
        .clear-button:hover {
          background: var(--color-border, #e5e7eb);
          color: var(--color-text, #1f2937);
          border-color: var(--color-text-muted, #9ca3af);
        }
        
        .clear-button:focus {
          outline: 2px solid var(--color-primary, #000);
          outline-offset: 2px;
        }
        
        .clear-button:active {
          transform: translateY(-50%) scale(0.95);
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
          margin-top: 1.5rem; /* Increased space from search button */
          margin-bottom: 1rem; /* Space before source chips */
        }

        .toggle-label {
          font-size: 14px;
          font-weight: 500;
          color: var(--color-text-muted);
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
          .search-form {
            max-width: 100%;
          }
          
          .search-icon {
            left: var(--space-3);
          }

          .search-input {
            padding-left: calc(var(--space-3) + 28px);
            padding-right: 44px;
            font-size: 1rem;
          }

          .clear-button {
            right: 12px;
            width: 26px;
            height: 26px;
          }
          
          .search-button {
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
            padding: var(--space-3);
            padding-left: calc(var(--space-3) + 24px);
            padding-right: 44px; /* Ensure text doesn't hide under clear button */
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
