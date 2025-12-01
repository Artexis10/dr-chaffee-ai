import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { VideoCard } from '../../src/components/VideoCard';

/**
 * Component tests for VideoCard - focusing on button rendering and accessibility.
 */

const mockGroup = {
  videoId: 'test123',
  videoTitle: 'Test Video Title',
  source_type: 'youtube',
  clips: [
    {
      id: 'clip1',
      text: 'This is a test transcript segment about carnivore diet.',
      start_time_seconds: 120,
      end_time_seconds: 150,
      similarity: 0.95,
      url: 'https://www.youtube.com/watch?v=test123',
      source_type: 'youtube',
    },
    {
      id: 'clip2',
      text: 'Another segment discussing meat-based nutrition.',
      start_time_seconds: 300,
      end_time_seconds: 330,
      similarity: 0.88,
      url: 'https://www.youtube.com/watch?v=test123',
      source_type: 'youtube',
    },
  ],
};

describe('VideoCard - Watch on YouTube Button', () => {
  const defaultProps = {
    group: mockGroup,
    query: 'carnivore',
    highlightSearchTerms: (text: string) => text,
    seekToTimestamp: vi.fn(),
    copyTimestampLink: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render Watch on YouTube links for YouTube videos', () => {
    render(<VideoCard {...defaultProps} />);
    
    const watchLinks = screen.getAllByText('Watch on YouTube');
    expect(watchLinks).toHaveLength(2); // One for each clip
  });

  it('should have correct href with timestamp', () => {
    render(<VideoCard {...defaultProps} />);
    
    const watchLinks = screen.getAllByText('Watch on YouTube');
    
    // First clip at 120 seconds
    expect(watchLinks[0].closest('a')).toHaveAttribute(
      'href',
      'https://www.youtube.com/watch?v=test123&t=120s'
    );
    
    // Second clip at 300 seconds
    expect(watchLinks[1].closest('a')).toHaveAttribute(
      'href',
      'https://www.youtube.com/watch?v=test123&t=300s'
    );
  });

  it('should open in new tab', () => {
    render(<VideoCard {...defaultProps} />);
    
    const watchLinks = screen.getAllByText('Watch on YouTube');
    
    watchLinks.forEach(link => {
      expect(link.closest('a')).toHaveAttribute('target', '_blank');
      expect(link.closest('a')).toHaveAttribute('rel', 'noopener noreferrer');
    });
  });

  it('should have watch-link class for styling', () => {
    render(<VideoCard {...defaultProps} />);
    
    const watchLinks = screen.getAllByText('Watch on YouTube');
    
    watchLinks.forEach(link => {
      // The link should have the watch-link class from CSS modules
      expect(link.closest('a')?.className).toContain('watch-link');
    });
  });

  it('should not render Watch on YouTube for non-YouTube sources', () => {
    const nonYouTubeGroup = {
      ...mockGroup,
      source_type: 'podcast',
    };
    
    render(<VideoCard {...defaultProps} group={nonYouTubeGroup} />);
    
    expect(screen.queryByText('Watch on YouTube')).not.toBeInTheDocument();
  });
});

describe('VideoCard - Timestamp Button', () => {
  const defaultProps = {
    group: mockGroup,
    query: 'carnivore',
    highlightSearchTerms: (text: string) => text,
    seekToTimestamp: vi.fn(),
    copyTimestampLink: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('should render timestamp buttons', () => {
    render(<VideoCard {...defaultProps} />);
    
    // 120 seconds = 2:00
    expect(screen.getByText('2:00')).toBeInTheDocument();
    // 300 seconds = 5:00
    expect(screen.getByText('5:00')).toBeInTheDocument();
  });

  it('should call seekToTimestamp when timestamp button is clicked', () => {
    const seekToTimestamp = vi.fn();
    render(<VideoCard {...defaultProps} seekToTimestamp={seekToTimestamp} />);
    
    const timestampButton = screen.getByText('2:00');
    fireEvent.click(timestampButton);
    
    expect(seekToTimestamp).toHaveBeenCalledWith('test123', 120);
  });

  it('should have title attribute for accessibility', () => {
    render(<VideoCard {...defaultProps} />);
    
    const timestampButtons = screen.getAllByTitle('Play this clip');
    expect(timestampButtons).toHaveLength(2);
  });
});

describe('VideoCard - Video Header', () => {
  const defaultProps = {
    group: mockGroup,
    query: 'carnivore',
    highlightSearchTerms: (text: string) => text,
    seekToTimestamp: vi.fn(),
    copyTimestampLink: vi.fn(),
  };

  it('should render video title', () => {
    render(<VideoCard {...defaultProps} />);
    
    expect(screen.getByText('Test Video Title')).toBeInTheDocument();
  });

  it('should render YouTube icon for YouTube videos', () => {
    render(<VideoCard {...defaultProps} />);
    
    expect(screen.getByText('📺')).toBeInTheDocument();
  });

  it('should render different icon for non-YouTube sources', () => {
    const podcastGroup = {
      ...mockGroup,
      source_type: 'podcast',
    };
    
    render(<VideoCard {...defaultProps} group={podcastGroup} />);
    
    expect(screen.getByText('💼')).toBeInTheDocument();
  });
});

describe('VideoCard - Transcript Text', () => {
  const defaultProps = {
    group: mockGroup,
    query: 'carnivore',
    highlightSearchTerms: vi.fn((text: string, query: string) => {
      return text.replace(
        new RegExp(`(${query})`, 'gi'),
        '<mark>$1</mark>'
      );
    }),
    seekToTimestamp: vi.fn(),
    copyTimestampLink: vi.fn(),
  };

  it('should render transcript text for each clip', () => {
    render(<VideoCard {...defaultProps} />);
    
    expect(screen.getByText(/This is a test transcript segment/)).toBeInTheDocument();
    expect(screen.getByText(/Another segment discussing/)).toBeInTheDocument();
  });

  it('should call highlightSearchTerms for each clip', () => {
    const highlightSearchTerms = vi.fn((text: string) => text);
    render(<VideoCard {...defaultProps} highlightSearchTerms={highlightSearchTerms} />);
    
    expect(highlightSearchTerms).toHaveBeenCalledTimes(2);
    expect(highlightSearchTerms).toHaveBeenCalledWith(
      'This is a test transcript segment about carnivore diet.',
      'carnivore'
    );
  });
});
