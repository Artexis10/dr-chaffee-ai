import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { AnswerCard } from '../../src/components/AnswerCard';

/**
 * Component tests for AnswerCard - focusing on citation rendering and date formatting.
 */

const mockCitations = [
  {
    index: 1,
    video_id: 'abc123',
    title: 'Test Video Title',
    t_start_s: 638,
    clip_time: '10:38',
    published_at: '2023-12-28T00:00:00Z',
  },
  {
    index: 2,
    video_id: 'def456',
    title: 'Another Video',
    t_start_s: 120,
    clip_time: '2:00',
    published_at: '2024-01-15T00:00:00Z',
  },
];

const mockAnswer = {
  answer_md: 'This is a test answer with citations [1] and [2].',
  citations: mockCitations,
  confidence: 0.85,
  used_chunk_ids: ['chunk1', 'chunk2'],
};

describe('AnswerCard - Citation Rendering', () => {
  const defaultProps = {
    answer: mockAnswer,
    loading: false,
    onPlayClip: vi.fn(),
    onCopyLink: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    // Mock fetch for stats endpoint
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ segments: 1000, videos: 50 }),
      })
    ) as unknown as typeof fetch;
  });

  it('should render the answer card with answer text', () => {
    render(<AnswerCard {...defaultProps} />);
    
    expect(screen.getByText(/This is a test answer/)).toBeInTheDocument();
  });

  it('should render citation chips as clickable buttons', () => {
    render(<AnswerCard {...defaultProps} />);
    
    // Look for citation chip buttons (now use .chip class, no brackets in text)
    const citationButtons = screen.getAllByRole('button');
    const citationChips = citationButtons.filter(btn => 
      btn.classList.contains('chip') && (btn.textContent === '1' || btn.textContent === '2')
    );
    
    expect(citationChips.length).toBeGreaterThan(0);
  });

  it('should show Citation Details toggle button', () => {
    render(<AnswerCard {...defaultProps} />);
    
    expect(screen.getByText('Citation Details')).toBeInTheDocument();
  });

  it('should show citation count in toggle button', () => {
    render(<AnswerCard {...defaultProps} />);
    
    expect(screen.getByText('(2)')).toBeInTheDocument();
  });

  it('should expand citation details when toggle is clicked', () => {
    render(<AnswerCard {...defaultProps} />);
    
    const toggleButton = screen.getByText('Citation Details').closest('button');
    expect(toggleButton).toBeInTheDocument();
    
    fireEvent.click(toggleButton!);
    
    // Should now show citation titles
    expect(screen.getByText('Test Video Title')).toBeInTheDocument();
    expect(screen.getByText('Another Video')).toBeInTheDocument();
  });

  it('should display formatted dates in citation details', () => {
    render(<AnswerCard {...defaultProps} />);
    
    const toggleButton = screen.getByText('Citation Details').closest('button');
    fireEvent.click(toggleButton!);
    
    // Should show formatted dates
    expect(screen.getByText('Dec 28, 2023')).toBeInTheDocument();
    expect(screen.getByText('Jan 15, 2024')).toBeInTheDocument();
  });

  it('should display clip times in citation details', () => {
    render(<AnswerCard {...defaultProps} />);
    
    const toggleButton = screen.getByText('Citation Details').closest('button');
    fireEvent.click(toggleButton!);
    
    expect(screen.getByText('10:38')).toBeInTheDocument();
    expect(screen.getByText('2:00')).toBeInTheDocument();
  });

  it('should call onPlayClip when play button is clicked', () => {
    const onPlayClip = vi.fn();
    render(<AnswerCard {...defaultProps} onPlayClip={onPlayClip} />);
    
    const toggleButton = screen.getByText('Citation Details').closest('button');
    fireEvent.click(toggleButton!);
    
    // Find and click a play button
    const playButtons = screen.getAllByTitle('Play this clip');
    fireEvent.click(playButtons[0]);
    
    expect(onPlayClip).toHaveBeenCalledWith('abc123', 638);
  });
});

describe('AnswerCard - Date Formatting Edge Cases', () => {
  beforeEach(() => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ segments: 1000, videos: 50 }),
      })
    ) as unknown as typeof fetch;
  });

  it('should show "Date unavailable" for null published_at', () => {
    const answerWithNullDate = {
      ...mockAnswer,
      citations: [{
        ...mockCitations[0],
        published_at: null,
      }],
    };
    
    render(<AnswerCard answer={answerWithNullDate} loading={false} />);
    
    const toggleButton = screen.getByText('Citation Details').closest('button');
    fireEvent.click(toggleButton!);
    
    expect(screen.getByText('Date unavailable')).toBeInTheDocument();
  });

  it('should show "Date unavailable" for "unknown" published_at', () => {
    const answerWithUnknownDate = {
      ...mockAnswer,
      citations: [{
        ...mockCitations[0],
        published_at: 'unknown' as any,
      }],
    };
    
    render(<AnswerCard answer={answerWithUnknownDate} loading={false} />);
    
    const toggleButton = screen.getByText('Citation Details').closest('button');
    fireEvent.click(toggleButton!);
    
    expect(screen.getByText('Date unavailable')).toBeInTheDocument();
  });

  it('should show "Date unavailable" for epoch date (1970-01-01)', () => {
    const answerWithEpochDate = {
      ...mockAnswer,
      citations: [{
        ...mockCitations[0],
        published_at: '1970-01-01',
      }],
    };
    
    render(<AnswerCard answer={answerWithEpochDate} loading={false} />);
    
    const toggleButton = screen.getByText('Citation Details').closest('button');
    fireEvent.click(toggleButton!);
    
    expect(screen.getByText('Date unavailable')).toBeInTheDocument();
  });
});

describe('AnswerCard - Empty Citations', () => {
  beforeEach(() => {
    global.fetch = vi.fn(() =>
      Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ segments: 1000, videos: 50 }),
      })
    ) as unknown as typeof fetch;
  });

  it('should show message when no citations are present', () => {
    const answerWithNoCitations = {
      ...mockAnswer,
      citations: [],
    };
    
    render(<AnswerCard answer={answerWithNoCitations} loading={false} />);
    
    const toggleButton = screen.getByText('Citation Details').closest('button');
    fireEvent.click(toggleButton!);
    
    expect(screen.getByText('No specific citations were referenced in this answer.')).toBeInTheDocument();
  });

  it('should show (0) in citation count when empty', () => {
    const answerWithNoCitations = {
      ...mockAnswer,
      citations: [],
    };
    
    render(<AnswerCard answer={answerWithNoCitations} loading={false} />);
    
    expect(screen.getByText('(0)')).toBeInTheDocument();
  });
});

describe('AnswerCard - Loading State', () => {
  it('should show loading indicator when loading', () => {
    render(<AnswerCard answer={null} loading={true} />);
    
    expect(screen.getByText('Generating Answer')).toBeInTheDocument();
  });

  it('should show elapsed time during loading', () => {
    render(<AnswerCard answer={null} loading={true} />);
    
    expect(screen.getByText('0s elapsed')).toBeInTheDocument();
  });
});

describe('AnswerCard - Error State', () => {
  it('should show error message when error prop is provided', () => {
    render(<AnswerCard answer={null} loading={false} error="Something went wrong" />);
    
    expect(screen.getByText('Unable to Generate Answer')).toBeInTheDocument();
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
  });
});
