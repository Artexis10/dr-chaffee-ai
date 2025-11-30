import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SearchBar } from '../../src/components/SearchBar';

/**
 * Component tests for SearchBar - focusing on answer style toggle logic.
 * These tests verify behavior, not visual styling.
 */

describe('SearchBar - Answer Style Toggle', () => {
  const defaultProps = {
    query: '',
    setQuery: vi.fn(),
    handleSearch: vi.fn(),
    loading: false,
    answerStyle: 'concise' as const,
    onAnswerStyleChange: vi.fn(),
    disabled: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render Short and Long toggle buttons', () => {
    render(<SearchBar {...defaultProps} />);
    
    expect(screen.getByText('Short')).toBeInTheDocument();
    expect(screen.getByText('Long')).toBeInTheDocument();
  });

  it('should have Short button active when answerStyle is concise', () => {
    render(<SearchBar {...defaultProps} answerStyle="concise" />);
    
    const shortButton = screen.getByText('Short');
    expect(shortButton).toHaveClass('active');
  });

  it('should have Long button active when answerStyle is detailed', () => {
    render(<SearchBar {...defaultProps} answerStyle="detailed" />);
    
    const longButton = screen.getByText('Long');
    expect(longButton).toHaveClass('active');
  });

  it('should call onAnswerStyleChange with "concise" when Short is clicked', () => {
    const onAnswerStyleChange = vi.fn();
    render(
      <SearchBar 
        {...defaultProps} 
        answerStyle="detailed" 
        onAnswerStyleChange={onAnswerStyleChange} 
      />
    );
    
    fireEvent.click(screen.getByText('Short'));
    expect(onAnswerStyleChange).toHaveBeenCalledWith('concise');
  });

  it('should call onAnswerStyleChange with "detailed" when Long is clicked', () => {
    const onAnswerStyleChange = vi.fn();
    render(
      <SearchBar 
        {...defaultProps} 
        answerStyle="concise" 
        onAnswerStyleChange={onAnswerStyleChange} 
      />
    );
    
    fireEvent.click(screen.getByText('Long'));
    expect(onAnswerStyleChange).toHaveBeenCalledWith('detailed');
  });

  it('should not call onAnswerStyleChange when disabled', () => {
    const onAnswerStyleChange = vi.fn();
    render(
      <SearchBar 
        {...defaultProps} 
        disabled={true} 
        onAnswerStyleChange={onAnswerStyleChange} 
      />
    );
    
    fireEvent.click(screen.getByText('Short'));
    fireEvent.click(screen.getByText('Long'));
    expect(onAnswerStyleChange).not.toHaveBeenCalled();
  });

  it('should not call onAnswerStyleChange when loading', () => {
    const onAnswerStyleChange = vi.fn();
    render(
      <SearchBar 
        {...defaultProps} 
        loading={true} 
        onAnswerStyleChange={onAnswerStyleChange} 
      />
    );
    
    fireEvent.click(screen.getByText('Short'));
    fireEvent.click(screen.getByText('Long'));
    expect(onAnswerStyleChange).not.toHaveBeenCalled();
  });

  it('should show "Answer style:" label', () => {
    render(<SearchBar {...defaultProps} />);
    
    expect(screen.getByText('Answer style:')).toBeInTheDocument();
  });
});

describe('SearchBar - Search Input', () => {
  const defaultProps = {
    query: '',
    setQuery: vi.fn(),
    handleSearch: vi.fn(),
    loading: false,
    answerStyle: 'concise' as const,
    onAnswerStyleChange: vi.fn(),
    disabled: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render search input', () => {
    render(<SearchBar {...defaultProps} />);
    
    expect(screen.getByLabelText('Search query')).toBeInTheDocument();
  });

  it('should call setQuery when typing', () => {
    const setQuery = vi.fn();
    render(<SearchBar {...defaultProps} setQuery={setQuery} />);
    
    const input = screen.getByLabelText('Search query');
    fireEvent.change(input, { target: { value: 'test query' } });
    
    expect(setQuery).toHaveBeenCalledWith('test query');
  });

  it('should not call setQuery when disabled', () => {
    const setQuery = vi.fn();
    render(<SearchBar {...defaultProps} setQuery={setQuery} disabled={true} />);
    
    const input = screen.getByLabelText('Search query');
    fireEvent.change(input, { target: { value: 'test query' } });
    
    expect(setQuery).not.toHaveBeenCalled();
  });

  it('should show search button', () => {
    render(<SearchBar {...defaultProps} />);
    
    expect(screen.getByRole('button', { name: /search/i })).toBeInTheDocument();
  });

  it('should show "Searching..." when loading', () => {
    render(<SearchBar {...defaultProps} loading={true} />);
    
    expect(screen.getByText('Searching...')).toBeInTheDocument();
  });

  it('should disable search button when query is empty', () => {
    render(<SearchBar {...defaultProps} query="" />);
    
    const button = screen.getByRole('button', { name: /^search$/i });
    expect(button).toBeDisabled();
  });

  it('should enable search button when query has content', () => {
    render(<SearchBar {...defaultProps} query="test" />);
    
    const button = screen.getByRole('button', { name: /^search$/i });
    expect(button).not.toBeDisabled();
  });
});
