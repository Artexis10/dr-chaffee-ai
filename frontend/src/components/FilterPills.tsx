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
            🔍 All
          </button>
          <button
            className={`filter-pill ${sourceFilter === 'youtube' ? 'active' : ''}`}
            onClick={() => !disabled && setSourceFilter('youtube')}
            aria-pressed={sourceFilter === 'youtube'}
            aria-label="Filter by YouTube only"
            disabled={disabled}
          >
            <svg width="18" height="18" viewBox="0 0 159 110" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M154 17.5c-1.82-6.73-7.07-12-13.8-13.8C128.4 0 79.5 0 79.5 0S30.6 0 18.8 3.7C12.07 5.5 6.82 10.77 5 17.5 1.5 29.4 1.5 55 1.5 55s0 25.6 3.5 37.5c1.82 6.73 7.07 12 13.8 13.8 11.8 3.7 60.7 3.7 60.7 3.7s48.9 0 60.7-3.7c6.73-1.8 11.98-7.07 13.8-13.8 3.5-11.9 3.5-37.5 3.5-37.5s0-25.6-3.5-37.5z" fill="#FF0000"/>
              <path d="M64 78.2V31.8L104.5 55 64 78.2z" fill="#FFFFFF"/>
            </svg>
            YouTube
          </button>
          <button
            className={`filter-pill ${sourceFilter === 'zoom' ? 'active' : ''}`}
            onClick={() => !disabled && setSourceFilter('zoom')}
            aria-pressed={sourceFilter === 'zoom'}
            aria-label="Filter by Zoom only"
            disabled={disabled}
          >
            <svg width="18" height="18" viewBox="0 0 512 512" fill="none" xmlns="http://www.w3.org/2000/svg">
              <rect width="512" height="512" rx="100" fill="#2D8CFF"/>
              <path d="M160 176h160v80l80-60v160l-80-60v80H160V176z" fill="white"/>
            </svg>
            Zoom
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
