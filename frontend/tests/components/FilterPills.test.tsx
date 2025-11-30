import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { FilterPills } from '../../src/components/FilterPills';

/**
 * Component tests for FilterPills - focusing on source selector logic.
 * These tests verify behavior, not visual styling.
 */

describe('FilterPills - Source Selector', () => {
  const defaultProps = {
    sourceFilter: 'all' as const,
    setSourceFilter: vi.fn(),
    yearFilter: 'all',
    setYearFilter: vi.fn(),
    availableYears: ['2024', '2023', '2022'],
    disabled: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render All, YouTube, and Zoom filter pills', () => {
    render(<FilterPills {...defaultProps} />);
    
    expect(screen.getByText('All')).toBeInTheDocument();
    expect(screen.getByText('YouTube')).toBeInTheDocument();
    expect(screen.getByText('Zoom')).toBeInTheDocument();
  });

  it('should have All pill active when sourceFilter is "all"', () => {
    render(<FilterPills {...defaultProps} sourceFilter="all" />);
    
    const allButton = screen.getByRole('button', { name: /all sources/i });
    expect(allButton).toHaveClass('active');
  });

  it('should have YouTube pill active when sourceFilter is "youtube"', () => {
    render(<FilterPills {...defaultProps} sourceFilter="youtube" />);
    
    const youtubeButton = screen.getByRole('button', { name: /youtube only/i });
    expect(youtubeButton).toHaveClass('active');
  });

  it('should have Zoom pill active when sourceFilter is "zoom"', () => {
    render(<FilterPills {...defaultProps} sourceFilter="zoom" />);
    
    const zoomButton = screen.getByRole('button', { name: /zoom only/i });
    expect(zoomButton).toHaveClass('active');
  });

  it('should call setSourceFilter with "all" when All is clicked', () => {
    const setSourceFilter = vi.fn();
    render(
      <FilterPills 
        {...defaultProps} 
        sourceFilter="youtube" 
        setSourceFilter={setSourceFilter} 
      />
    );
    
    fireEvent.click(screen.getByRole('button', { name: /all sources/i }));
    expect(setSourceFilter).toHaveBeenCalledWith('all');
  });

  it('should call setSourceFilter with "youtube" when YouTube is clicked', () => {
    const setSourceFilter = vi.fn();
    render(
      <FilterPills 
        {...defaultProps} 
        sourceFilter="all" 
        setSourceFilter={setSourceFilter} 
      />
    );
    
    fireEvent.click(screen.getByRole('button', { name: /youtube only/i }));
    expect(setSourceFilter).toHaveBeenCalledWith('youtube');
  });

  it('should call setSourceFilter with "zoom" when Zoom is clicked', () => {
    const setSourceFilter = vi.fn();
    render(
      <FilterPills 
        {...defaultProps} 
        sourceFilter="all" 
        setSourceFilter={setSourceFilter} 
      />
    );
    
    fireEvent.click(screen.getByRole('button', { name: /zoom only/i }));
    expect(setSourceFilter).toHaveBeenCalledWith('zoom');
  });

  it('should not call setSourceFilter when disabled', () => {
    const setSourceFilter = vi.fn();
    render(
      <FilterPills 
        {...defaultProps} 
        disabled={true} 
        setSourceFilter={setSourceFilter} 
      />
    );
    
    fireEvent.click(screen.getByRole('button', { name: /all sources/i }));
    fireEvent.click(screen.getByRole('button', { name: /youtube only/i }));
    fireEvent.click(screen.getByRole('button', { name: /zoom only/i }));
    
    expect(setSourceFilter).not.toHaveBeenCalled();
  });

  it('should have correct aria-pressed attribute for active pill', () => {
    render(<FilterPills {...defaultProps} sourceFilter="youtube" />);
    
    const allButton = screen.getByRole('button', { name: /all sources/i });
    const youtubeButton = screen.getByRole('button', { name: /youtube only/i });
    const zoomButton = screen.getByRole('button', { name: /zoom only/i });
    
    expect(allButton).toHaveAttribute('aria-pressed', 'false');
    expect(youtubeButton).toHaveAttribute('aria-pressed', 'true');
    expect(zoomButton).toHaveAttribute('aria-pressed', 'false');
  });

  it('selecting one source should deselect others (mutual exclusivity)', () => {
    const setSourceFilter = vi.fn();
    const { rerender } = render(
      <FilterPills 
        {...defaultProps} 
        sourceFilter="all" 
        setSourceFilter={setSourceFilter} 
      />
    );
    
    // Click YouTube
    fireEvent.click(screen.getByRole('button', { name: /youtube only/i }));
    expect(setSourceFilter).toHaveBeenCalledWith('youtube');
    
    // Simulate state update
    rerender(
      <FilterPills 
        {...defaultProps} 
        sourceFilter="youtube" 
        setSourceFilter={setSourceFilter} 
      />
    );
    
    // Verify only YouTube is active
    expect(screen.getByRole('button', { name: /all sources/i })).not.toHaveClass('active');
    expect(screen.getByRole('button', { name: /youtube only/i })).toHaveClass('active');
    expect(screen.getByRole('button', { name: /zoom only/i })).not.toHaveClass('active');
  });
});

describe('FilterPills - Year Filter', () => {
  const defaultProps = {
    sourceFilter: 'all' as const,
    setSourceFilter: vi.fn(),
    yearFilter: 'all',
    setYearFilter: vi.fn(),
    availableYears: ['2024', '2023', '2022'],
    disabled: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render year dropdown when years are available', () => {
    render(<FilterPills {...defaultProps} />);
    
    expect(screen.getByLabelText('Filter by year')).toBeInTheDocument();
  });

  it('should not render year dropdown when no years available', () => {
    render(<FilterPills {...defaultProps} availableYears={[]} />);
    
    expect(screen.queryByLabelText('Filter by year')).not.toBeInTheDocument();
  });

  it('should show "All Years" option', () => {
    render(<FilterPills {...defaultProps} />);
    
    expect(screen.getByText('All Years')).toBeInTheDocument();
  });

  it('should show all available years as options', () => {
    render(<FilterPills {...defaultProps} />);
    
    expect(screen.getByText('2024')).toBeInTheDocument();
    expect(screen.getByText('2023')).toBeInTheDocument();
    expect(screen.getByText('2022')).toBeInTheDocument();
  });

  it('should call setYearFilter when year is selected', () => {
    const setYearFilter = vi.fn();
    render(<FilterPills {...defaultProps} setYearFilter={setYearFilter} />);
    
    const select = screen.getByLabelText('Filter by year');
    fireEvent.change(select, { target: { value: '2023' } });
    
    expect(setYearFilter).toHaveBeenCalledWith('2023');
  });

  it('should not call setYearFilter when disabled', () => {
    const setYearFilter = vi.fn();
    render(<FilterPills {...defaultProps} disabled={true} setYearFilter={setYearFilter} />);
    
    const select = screen.getByLabelText('Filter by year');
    fireEvent.change(select, { target: { value: '2023' } });
    
    expect(setYearFilter).not.toHaveBeenCalled();
  });
});
