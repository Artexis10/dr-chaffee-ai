/*
 * UI Theme Guardrail:
 * DO NOT modify this file unless Hugo explicitly instructs.
 * This file defines the locked-in Dr Chaffee visual system.
 * See: frontend/docs/ui-theme-guidelines.md
 */

import React from 'react';

interface FilterPillsProps {
  sourceFilter: 'all' | 'youtube' | 'zoom';
  setSourceFilter: React.Dispatch<React.SetStateAction<'all' | 'youtube' | 'zoom'>>;
  yearFilter: string;
  setYearFilter: (filter: string) => void;
  availableYears: string[];
  disabled?: boolean; // Disable all interactions while search is running
}

export const FilterPills: React.FC<FilterPillsProps> = ({ 
  sourceFilter, 
  setSourceFilter, 
  yearFilter, 
  setYearFilter,
  availableYears,
  disabled = false
}) => {
  const disabledStyle = disabled ? { opacity: 0.5, pointerEvents: 'none' as const, cursor: 'not-allowed' } : {};
  
  return (
    <div className="filter-container" style={disabledStyle}>
      <div className="filter-group">
        <span className="filter-label">Source:</span>
        <div className="filter-pills">
          <button
            className={`filter-pill ${sourceFilter === 'all' ? 'active' : ''}`}
            onClick={() => !disabled && setSourceFilter('all')}
            aria-pressed={sourceFilter === 'all'}
            aria-label="Filter by all sources"
            disabled={disabled}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <circle cx="11" cy="11" r="8" stroke="currentColor" strokeWidth="2"/>
              <path d="M21 21l-4.35-4.35" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            </svg>
            <span>All</span>
          </button>
          <button
            className={`filter-pill ${sourceFilter === 'youtube' ? 'active' : ''}`}
            onClick={() => !disabled && setSourceFilter('youtube')}
            aria-pressed={sourceFilter === 'youtube'}
            aria-label="Filter by YouTube only"
            disabled={disabled}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M22.54 6.42a2.78 2.78 0 0 0-1.94-2C18.88 4 12 4 12 4s-6.88 0-8.6.46a2.78 2.78 0 0 0-1.94 2A29 29 0 0 0 1 11.75a29 29 0 0 0 .46 5.33A2.78 2.78 0 0 0 3.4 19c1.72.46 8.6.46 8.6.46s6.88 0 8.6-.46a2.78 2.78 0 0 0 1.94-2 29 29 0 0 0 .46-5.25 29 29 0 0 0-.46-5.33z" stroke="currentColor" strokeWidth="1.5" fill="none"/>
              <polygon points="9.75,15.02 15.5,11.75 9.75,8.48" fill="currentColor"/>
            </svg>
            <span>YouTube</span>
          </button>
          <button
            className={`filter-pill ${sourceFilter === 'zoom' ? 'active' : ''}`}
            onClick={() => !disabled && setSourceFilter('zoom')}
            aria-pressed={sourceFilter === 'zoom'}
            aria-label="Filter by Zoom only"
            disabled={disabled}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <rect x="2" y="6" width="14" height="12" rx="2" stroke="currentColor" strokeWidth="1.5" fill="none"/>
              <path d="M16 9.5l4-2.5v10l-4-2.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            <span>Zoom</span>
          </button>
        </div>
      </div>
      
      {availableYears.length > 0 && (
        <div className="filter-group">
          <span className="filter-label">Year:</span>
          <select
            className="year-filter"
            value={yearFilter}
            onChange={(e) => !disabled && setYearFilter(e.target.value)}
            aria-label="Filter by year"
            disabled={disabled}
          >
            <option value="all">All Years</option>
            {availableYears.map((year) => (
              <option key={year} value={year}>
                {year}
              </option>
            ))}
          </select>
        </div>
      )}
    </div>
  );
};
