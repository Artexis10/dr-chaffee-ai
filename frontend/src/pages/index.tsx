import { useState, useEffect, useCallback, useRef, lazy, Suspense } from 'react';
import Head from 'next/head';
import Image from 'next/image';
import { SearchBar } from '../components/SearchBar';
import { FilterPills } from '../components/FilterPills';
import { LoadingSkeleton } from '../components/LoadingSkeleton';
import { Footer } from '../components/Footer';
import { ErrorBoundary } from '../components/ErrorBoundary';
import { DarkModeToggle } from '../components/DarkModeToggle';
import { DisclaimerBanner } from '../components/DisclaimerBanner';
import { SearchResult, VideoGroup } from '../types';
import { analytics, setupAnalyticsListeners, trackEvent } from '../utils/analytics';
import Link from 'next/link';

// Lazy load components that aren't needed for initial render
const SearchResults = lazy(() => import('../components/SearchResults').then(mod => ({ default: mod.SearchResults })));
const AnswerCard = lazy(() => import('../components/AnswerCard').then(mod => ({ default: mod.AnswerCard })));

// Simple fallback component for lazy-loaded components
const LazyLoadFallback = () => <div className="lazy-load-placeholder"></div>;

export default function Home() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [sourceFilter, setSourceFilter] = useState<'all' | 'youtube' | 'zoom'>('all');
  const [yearFilter, setYearFilter] = useState<string>('all');
  const [availableYears, setAvailableYears] = useState<string[]>([]);
  const [selectedResultIndex, setSelectedResultIndex] = useState(-1);
  const [totalResults, setTotalResults] = useState(0);
  const [groupedResults, setGroupedResults] = useState<VideoGroup[]>([]);
  const [copySuccess, setCopySuccess] = useState('');
  const [showCopyNotification, setShowCopyNotification] = useState(false);
  const [answerData, setAnswerData] = useState<any>(null);
  const [answerLoading, setAnswerLoading] = useState(false);
  const [answerError, setAnswerError] = useState('');
  const [answerCancelled, setAnswerCancelled] = useState(false);
  const [answerStyle, setAnswerStyle] = useState<'concise' | 'detailed'>('concise');
  const searchInputRef = useRef<HTMLInputElement>(null);
  const copyNotificationTimeout = useRef<NodeJS.Timeout | null>(null);

  // Unified search state - true when any search operation is in progress
  const isSearching = loading || answerLoading;

  // Global error handlers to prevent popup errors
  useEffect(() => {
    const handleError = (event: ErrorEvent) => {
      console.error('Global error caught:', event.error);
      event.preventDefault(); // Prevent the error popup
      return false;
    };

    const handleUnhandledRejection = (event: PromiseRejectionEvent) => {
      console.error('Unhandled promise rejection caught:', event.reason);
      event.preventDefault(); // Prevent the error popup
      return false;
    };

    window.addEventListener('error', handleError);
    window.addEventListener('unhandledrejection', handleUnhandledRejection);

    return () => {
      window.removeEventListener('error', handleError);
      window.removeEventListener('unhandledrejection', handleUnhandledRejection);
    };
  }, []);
  
  // Initialize theme on mount - sync with tuning dashboard (default to DARK)
  useEffect(() => {
    const THEME_KEY = 'askdrchaffee.theme';
    const storedTheme = localStorage.getItem(THEME_KEY);
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    // Determine initial theme: stored > system preference > default DARK
    let shouldBeDark: boolean;
    if (storedTheme === 'dark') {
      shouldBeDark = true;
    } else if (storedTheme === 'light') {
      shouldBeDark = false;
    } else {
      // No stored preference - default to DARK unless system explicitly prefers light
      shouldBeDark = prefersDark !== false;
    }
    
    const root = document.documentElement;
    if (shouldBeDark) {
      root.classList.add('dark-mode');
      root.classList.remove('light-mode');
    } else {
      root.classList.remove('dark-mode');
      root.classList.add('light-mode');
    }
    
    // Persist if not already stored
    if (!storedTheme) {
      localStorage.setItem(THEME_KEY, shouldBeDark ? 'dark' : 'light');
    }
  }, []);

  // Initialize analytics
  useEffect(() => {
    // Initialize analytics with debug mode in development
    analytics.init({ debug: process.env.NODE_ENV === 'development' });
    
    // Set up event listeners for tracking user interactions
    setupAnalyticsListeners();
    
    // Track page load event
    trackEvent('page_loaded', {
      timestamp: new Date().toISOString(),
      userAgent: navigator.userAgent
    });
    
    return () => {
      // Track page unload event
      trackEvent('page_unloaded');
    };
  }, []);

  // Throttling mechanism to prevent rate limits
  const lastRequestTime = useRef<number>(0);
  const MIN_REQUEST_INTERVAL = 5000; // 5 seconds between requests to stay well under the 500 RPM limit
  
  // Loading timeout to prevent infinite loading
  const loadingTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  
  // Debug query state changes
  const handleSetQuery = useCallback((newQuery: string) => {
    console.log('Home: setQuery called with:', newQuery);
    setQuery(newQuery);
  }, []);

  useEffect(() => {
    console.log('Home: query state changed to:', query);
  }, [query]);

  // Function to extract years from results
  const extractYears = useCallback((results: SearchResult[]) => {
    const yearsSet = new Set<string>();
    results.forEach((result) => {
      if (result.published_at) {
        const year = new Date(result.published_at).getFullYear().toString();
        yearsSet.add(year);
      }
    });
    return Array.from(yearsSet).sort((a, b) => b.localeCompare(a)); // Sort descending
  }, []);

  // Function to group results by video
  const groupResultsByVideo = useCallback((results: SearchResult[]): VideoGroup[] => {
    const groups: { [key: string]: VideoGroup } = {};
    
    results.forEach((result) => {
      // Extract videoId - prefer video_id field if available (from source_clips)
      let videoId = '';
      let videoTitle = result.title || 'Unknown Video';
      
      // Check if result has video_id field (from answer API source_clips)
      if ((result as any).video_id) {
        videoId = (result as any).video_id;
      } else if (result.source_type === 'youtube' && result.url) {
        // Extract from URL for regular search results
        const match = result.url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&]+)/);
        if (match && match[1]) {
          videoId = match[1];
        }
      } else {
        // For non-YouTube sources, use the result ID as a unique identifier
        videoId = result.id;
      }
      
      if (!groups[videoId]) {
        groups[videoId] = {
          videoId,
          videoTitle,
          source_type: result.source_type,
          url: result.url,
          clips: []
        };
      }
      
      groups[videoId].clips.push(result);
    });
    
    // Convert to array and sort by relevance (using the highest similarity clip in each group)
    return Object.values(groups).sort((a, b) => {
      const aMaxSimilarity = Math.max(...a.clips.map(clip => clip.similarity));
      const bMaxSimilarity = Math.max(...b.clips.map(clip => clip.similarity));
      return bMaxSimilarity - aMaxSimilarity;
    });
  }, []);

  // Function to handle answer API call with retry logic and rate limiting
  const performAnswerWithRetry = useCallback(async (query: string, maxRetries: number = 5, styleOverride?: 'concise' | 'detailed') => {
    if (!query.trim()) return;
    
    // Check if enough time has passed since last request
    const now = Date.now();
    const timeSinceLastRequest = now - lastRequestTime.current;
    
    if (timeSinceLastRequest < MIN_REQUEST_INTERVAL) {
      const waitTime = MIN_REQUEST_INTERVAL - timeSinceLastRequest;
      console.log(`Throttling: waiting ${waitTime}ms before next request`);
      await new Promise(resolve => setTimeout(resolve, waitTime));
    }
    
    lastRequestTime.current = Date.now();
    
    setAnswerLoading(true);
    setAnswerError('');
    
    let attempt = 0;
    
    while (attempt < maxRetries) {
      try {
        console.log(`Answer API attempt ${attempt + 1}/${maxRetries}...`);
        
        const currentStyle = styleOverride || answerStyle;
        
        console.log(`📊 Using answer style: ${currentStyle}`);
        console.log('Answer API call URL:', `/api/answer`);
        
        // Add timeout to the fetch request
        const controller = new AbortController();
        // Detailed answers need more time (can take 60-90s with 2000-3000 words)
        // 3 minutes for detailed to handle large responses, 45s for concise
        const timeoutMs = currentStyle === 'detailed' ? 180000 : 45000;
        const timeoutId = setTimeout(() => controller.abort(), timeoutMs);
        
        console.log(`[Answer Request] Timeout set to ${timeoutMs}ms (${Math.round(timeoutMs/1000)}s) for ${currentStyle} style`);
        
        const response = await fetch(`/api/answer`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            query: query.trim(),
            style: currentStyle,
            top_k: 100  // Increased from 50 to 100 for better coverage
          }),
          signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        let responseData;
        
        try {
          // Read the response body only once
          responseData = await response.json();
        } catch (error) {
          const jsonError = error as Error;
          console.error('Failed to parse response as JSON:', jsonError);
          
          // Check if this is an AbortError (timeout)
          if (jsonError.name === 'AbortError' || jsonError.message.includes('abort')) {
            setAnswerError('Request timed out. The server might be unavailable or overloaded.');
            
            // If we're in development, show a more helpful message
            if (process.env.NODE_ENV === 'development') {
              setAnswerError('API request timed out. Make sure your backend services are running properly.');
            }
          } else {
            setAnswerError(`Failed to parse response: ${jsonError.message}`);
          }
          
          return; // Exit the function
        }
        
        if (!response.ok) {
          // Handle rate limit specifically
          if (response.status === 429 || (responseData?.error && responseData.error.toLowerCase().includes('rate limit'))) {
            if (attempt < maxRetries - 1) {
              // More aggressive exponential backoff: 5s, 10s, 20s, 40s, 80s
              const backoffTime = Math.pow(2, attempt) * 5000;
              console.log(`Rate limited. Retrying in ${backoffTime}ms...`);
              setAnswerError(`Rate limited. Retrying in ${Math.ceil(backoffTime / 1000)} seconds...`);
              await new Promise(resolve => setTimeout(resolve, backoffTime));
              attempt++;
              continue;
            } else {
              // Don't throw, just set the error state
              setAnswerError('OpenAI API rate limit reached. The service is limited to 500 requests per minute. Please try again in a few minutes.');
              return; // Exit the function
            }
          }
          
          // Don't throw, just set the error state
          setAnswerError(responseData?.error || `Answer failed with status: ${response.status}`);
          return; // Exit the function
        }
        
        console.log('Answer API response:', responseData);
        
        if (responseData && (responseData.answer || responseData.citations)) {
          setAnswerData(responseData);
          setAnswerError(''); // Clear any previous error messages
          
          // Set the source clips as search results so they show in "Supporting Video Clips"
          if (responseData.source_clips && Array.isArray(responseData.source_clips)) {
            console.log(`Setting ${responseData.source_clips.length} source clips as search results`);
            setResults(responseData.source_clips);
            setTotalResults(responseData.source_clips.length);
            
            // Group by video
            const grouped = groupResultsByVideo(responseData.source_clips);
            setGroupedResults(grouped);
          }
          
          break; // Success, exit retry loop
        } else {
          // Don't throw, just set the error state
          setAnswerError('No answer data received');
          return; // Exit the function
        }
        
      } catch (err) {
        console.error(`Answer API error (attempt ${attempt + 1}):`, err);
        
        const error = err as Error;
        const errorMessage = error.message || 'Answer request failed';
        
        // Handle network/connection errors specifically
        if (error.name === 'TypeError' && errorMessage.includes('fetch')) {
          setAnswerError('Unable to connect to the server. Please check your internet connection.');
          
          // If we're in development, show a more helpful message
          if (process.env.NODE_ENV === 'development') {
            setAnswerError('API connection failed. Make sure your backend services are running properly.');
          }
          
          return; // Exit the function
        }
        
        // If it's the last attempt or not a retryable error, set final error
        if (attempt === maxRetries - 1 || !errorMessage.toLowerCase().includes('rate limit')) {
          setAnswerError(`Something went wrong: ${errorMessage}`);
          return; // Exit the function instead of breaking
        }
        
        // Show a user-friendly message during retries
        setAnswerError(`Retrying... (attempt ${attempt + 1} of ${maxRetries})`);
        attempt++;
      }
    }
    
    setAnswerLoading(false);
    
    // Clear loading timeout when answer generation completes
    if (loadingTimeoutRef.current) {
      clearTimeout(loadingTimeoutRef.current);
      loadingTimeoutRef.current = null;
    }
  }, []);

  // Handler for cancelling answer generation
  const handleCancelAnswer = useCallback(() => {
    setAnswerLoading(false);
    setAnswerCancelled(true);
    setAnswerError('Answer generation cancelled by user.');
    
    // Track cancellation in analytics
    trackEvent('answer_cancelled', {
      query,
      timeElapsed: Date.now() - lastRequestTime.current
    });
  }, [query, trackEvent]);
  
  // Legacy function for backward compatibility
  const performAnswer = useCallback(async (query: string) => {
    return performAnswerWithRetry(query);
  }, [performAnswerWithRetry]);

  // Function to perform search API call
  const performSearch = useCallback(async (searchQuery: string, currentSourceFilter: string, currentYearFilter: string) => {
    if (!searchQuery.trim()) return;
    
    console.log('Starting search for:', searchQuery, 'with filters:', { currentSourceFilter, currentYearFilter });
    
    setLoading(true);
    setError('');
    
    try {
      const params = new URLSearchParams({
        q: searchQuery,
        ...(currentSourceFilter !== 'all' && { source_filter: currentSourceFilter }),
        ...(currentYearFilter !== 'all' && { year_filter: currentYearFilter })
      });
      
      console.log('API call URL:', `/api/search?${params}`);
      
      const response = await fetch(`/api/search?${params}`);
      
      let data;
      try {
        data = await response.json();
      } catch (jsonError) {
        console.error('Failed to parse search response as JSON:', jsonError);
        setError('Failed to parse search results. Please try again.');
        setResults([]);
        setGroupedResults([]);
        setTotalResults(0);
        return;
      }
      
      if (!response.ok) {
        // Handle error but don't throw
        console.error(`Search failed with status: ${response.status}`, data);
        
        // Show a user-friendly error message based on status code
        if (response.status === 503) {
          setError('Database service is currently unavailable. Please try again later.');
        } else if (response.status === 500) {
          setError('Search service encountered an error. Our team has been notified.');
        } else if (data && data.message) {
          setError(data.message);
        } else if (data && data.error) {
          setError(data.error);
        } else {
          setError('Search service error. Please try again later.');
        }
        
        // Set empty results but don't stop the answer generation
        setResults([]);
        setGroupedResults([]);
        setTotalResults(0);
        return;
      }
      console.log('API response:', data);
      console.log('Raw results length:', data.results ? data.results.length : 'undefined');
      
      const results = data.results || [];
      console.log('Processed results:', results.length);
      
      let years: string[] = [];
      let grouped: VideoGroup[] = [];
      
      try {
        years = extractYears(results);
        console.log('Extracted years:', years);
      } catch (yearError) {
        console.error('Error extracting years:', yearError);
      }
      
      try {
        grouped = groupResultsByVideo(results);
        console.log('Grouped results:', grouped.length);
      } catch (groupError) {
        console.error('Error grouping results:', groupError);
      }
      
      // Update state all at once with new results
      console.log('Updating state with:', { 
        resultsLength: results.length, 
        groupedLength: grouped.length 
      });
      
      setResults(results);
      setTotalResults(results.length);
      setAvailableYears(years);
      setGroupedResults(grouped);
      
      console.log('State update complete');
      
    } catch (err) {
      console.error('Search error:', err);
      setError(err instanceof Error ? err.message : 'An unknown error occurred');
      setResults([]);
      setGroupedResults([]);
      setTotalResults(0);
    } finally {
      setLoading(false);
      
      // Clear loading timeout when search completes
      if (loadingTimeoutRef.current) {
        clearTimeout(loadingTimeoutRef.current);
        loadingTimeoutRef.current = null;
      }
    }
  }, [extractYears, groupResultsByVideo]);

  // Clear results when query is empty (no debouncing)
  useEffect(() => {
    if (!query.trim()) {
      setResults([]);
      setGroupedResults([]);
      setTotalResults(0);
      setAnswerData(null);
      setAnswerError('');
    }
  }, [query]);

  // Function to handle search form submission with throttling
  const handleSearch = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    
    // Reset cancelled state when starting a new search
    setAnswerCancelled(false);
    
    // Check if we should throttle this request
    const now = Date.now();
    const timeSinceLastRequest = now - lastRequestTime.current;
    
    if (timeSinceLastRequest < MIN_REQUEST_INTERVAL) {
      const waitTime = Math.ceil((MIN_REQUEST_INTERVAL - timeSinceLastRequest) / 1000);
      setError(`Please wait ${waitTime} seconds before searching again to avoid rate limits.`);
      return;
    }
    
    // Clear any existing loading timeout
    if (loadingTimeoutRef.current) {
      clearTimeout(loadingTimeoutRef.current);
    }
    
    // Set a timeout to clear loading state after 30 seconds
    loadingTimeoutRef.current = setTimeout(() => {
      if (loading) {
        setLoading(false);
        setError('Request timed out. Please try again or refresh the page.');
      }
      if (answerLoading) {
        setAnswerLoading(false);
        setAnswerError('Answer generation timed out. Please try again or refresh the page.');
      }
    }, 30000); // 30 seconds timeout
    
    // Track search event with analytics
    trackEvent('search_submitted', {
      query,
      sourceFilter,
      yearFilter,
      timestamp: new Date().toISOString()
    });
    
    // Run search and answer in parallel, independently with full error isolation
    Promise.resolve().then(async () => {
      try {
        await performSearch(query, sourceFilter, yearFilter);
        
        // Track successful search
        trackEvent('search_results_loaded', {
          query,
          resultCount: totalResults,
          sourceFilter,
          yearFilter
        });
      } catch (err) {
        console.error('Search failed:', err);
        setError(err instanceof Error ? err.message : 'Search failed');
        
        // Track search error
        trackEvent('search_error', {
          query,
          error: err instanceof Error ? err.message : 'Unknown error',
          sourceFilter,
          yearFilter
        });
      }
    }).catch(err => {
      console.error('Search promise failed:', err);
      setError('Search encountered an error');
    });
    
    Promise.resolve().then(async () => {
      try {
        await performAnswerWithRetry(query, 5, answerStyle); // Pass current answer style
        
        // Track successful answer generation
        if (answerData) {
          trackEvent('answer_generated', {
            query,
            confidence: answerData.confidence,
            citationCount: answerData.citations?.length || 0,
            cached: answerData.cached || false
          });
        }
      } catch (err) {
        console.error('Answer failed:', err);
        // Answer failure doesn't affect search results
        
        // Track answer error
        trackEvent('answer_error', {
          query,
          error: err instanceof Error ? err.message : 'Unknown error'
        });
      }
    }).catch(err => {
      console.error('Answer promise failed:', err);
    });
  }, [query, sourceFilter, yearFilter, performSearch, performAnswerWithRetry, totalResults, answerData, answerStyle]);

  // Function to highlight search terms in text
  const highlightSearchTerms = (text: string, query: string): string => {
    if (!query.trim()) return text;
    
    const terms = query.trim().split(/\s+/).filter(term => term.length > 2);
    let highlightedText = text;
    
    terms.forEach(term => {
      // Escape special regex characters to prevent syntax errors
      const escapedTerm = term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      try {
        const regex = new RegExp(`(${escapedTerm})`, 'gi');
        highlightedText = highlightedText.replace(regex, '<mark>$1</mark>');
      } catch (e) {
        // If regex still fails, skip highlighting for this term
        console.warn('Failed to highlight term:', term, e);
      }
    });
    
    return highlightedText;
  };

  // Function to seek to a specific timestamp in YouTube video
  const seekToTimestamp = (videoId: string, seconds: number) => {
    console.log(`🎬 seekToTimestamp called: videoId=${videoId}, seconds=${seconds}`);
    
    if (typeof window !== 'undefined') {
      const iframe = document.querySelector(`iframe[src*="${videoId}"]`) as HTMLIFrameElement;
      
      if (iframe && iframe.contentWindow) {
        console.log('✅ Found iframe, sending seekTo command');
        iframe.contentWindow.postMessage(JSON.stringify({
          event: 'command',
          func: 'seekTo',
          args: [seconds, true]
        }), '*');
        
        // Scroll to the video player
        iframe.scrollIntoView({ behavior: 'smooth', block: 'center' });
      } else {
        console.log('⚠️ No iframe found, opening YouTube in new tab');
        // No embedded player found, open YouTube directly
        window.open(`https://www.youtube.com/watch?v=${videoId}&t=${Math.floor(seconds)}s`, '_blank');
      }
    }
  };

  // Function to copy timestamp link to clipboard
  const copyTimestampLink = (url: string) => {
    if (typeof navigator !== 'undefined' && navigator.clipboard) {
      navigator.clipboard.writeText(url)
        .then(() => {
          setCopySuccess('Link copied to clipboard!');
          setShowCopyNotification(true);
          
          if (copyNotificationTimeout.current) {
            clearTimeout(copyNotificationTimeout.current);
          }
          
          copyNotificationTimeout.current = setTimeout(() => {
            setShowCopyNotification(false);
          }, 2000);
        })
        .catch(() => {
          setCopySuccess('Failed to copy link');
          setShowCopyNotification(true);
          
          if (copyNotificationTimeout.current) {
            clearTimeout(copyNotificationTimeout.current);
          }
          
          copyNotificationTimeout.current = setTimeout(() => {
            setShowCopyNotification(false);
          }, 2000);
        });
    }
  };

  // Cleanup timeouts on unmount
  useEffect(() => {
    return () => {
      // Clear copy notification timeout
      if (copyNotificationTimeout.current) {
        clearTimeout(copyNotificationTimeout.current);
      }
      
      // Clear loading timeout
      if (loadingTimeoutRef.current) {
        clearTimeout(loadingTimeoutRef.current);
      }
    };
  }, []);

  // Handle keyboard navigation
  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.key === 'Enter' && selectedResultIndex >= 0) {
      const selectedResult = results[selectedResultIndex];
      if (!selectedResult) return;
      
      // Find the group this result belongs to
      const groupedResult = groupedResults.find(group => 
        group.clips.some(clip => clip.id === selectedResult.id)
      );
      
      if (groupedResult && selectedResult.source_type === 'youtube') {
        // Enter: Play in embedded player
        seekToTimestamp(groupedResult.videoId, Math.floor(selectedResult.start_time_seconds));
      }
    }
  };

  // Add keyboard event listener
  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [selectedResultIndex, results, groupedResults]);

  // Note: Filters are applied when user explicitly searches (no auto-search)

  return (
    <>
      <Head>
        <title>Ask Dr. Chaffee | Interactive Knowledge Base</title>
        <meta name="description" content="Interactive knowledge base with AI-powered answers from Dr Anthony Chaffee's content" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.ico" />
      </Head>

      <main className="container">
        <div className="header">
          <div className="header-top-bar">
            <Link href="/tuning" className="nav-link" title="Go to Tuning Dashboard">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 15C13.6569 15 15 13.6569 15 12C15 10.3431 13.6569 9 12 9C10.3431 9 9 10.3431 9 12C9 13.6569 10.3431 15 12 15Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                <path d="M19.4 15C19.2669 15.3016 19.2272 15.6362 19.286 15.9606C19.3448 16.285 19.4995 16.5843 19.73 16.82L19.79 16.88C19.976 17.0657 20.1235 17.2863 20.2241 17.5291C20.3248 17.7719 20.3766 18.0322 20.3766 18.295C20.3766 18.5578 20.3248 18.8181 20.2241 19.0609C20.1235 19.3037 19.976 19.5243 19.79 19.71C19.6043 19.896 19.3837 20.0435 19.1409 20.1441C18.8981 20.2448 18.6378 20.2966 18.375 20.2966C18.1122 20.2966 17.8519 20.2448 17.6091 20.1441C17.3663 20.0435 17.1457 19.896 16.96 19.71L16.9 19.65C16.6643 19.4195 16.365 19.2648 16.0406 19.206C15.7162 19.1472 15.3816 19.1869 15.08 19.32C14.7842 19.4468 14.532 19.6572 14.3543 19.9255C14.1766 20.1938 14.0813 20.5082 14.08 20.83V21C14.08 21.5304 13.8693 22.0391 13.4942 22.4142C13.1191 22.7893 12.6104 23 12.08 23C11.5496 23 11.0409 22.7893 10.6658 22.4142C10.2907 22.0391 10.08 21.5304 10.08 21V20.91C10.0723 20.579 9.96512 20.258 9.77251 19.9887C9.5799 19.7194 9.31074 19.5143 9 19.4C8.69838 19.2669 8.36381 19.2272 8.03941 19.286C7.71502 19.3448 7.41568 19.4995 7.18 19.73L7.12 19.79C6.93425 19.976 6.71368 20.1235 6.47088 20.2241C6.22808 20.3248 5.96783 20.3766 5.705 20.3766C5.44217 20.3766 5.18192 20.3248 4.93912 20.2241C4.69632 20.1235 4.47575 19.976 4.29 19.79C4.10405 19.6043 3.95653 19.3837 3.85588 19.1409C3.75523 18.8981 3.70343 18.6378 3.70343 18.375C3.70343 18.1122 3.75523 17.8519 3.85588 17.6091C3.95653 17.3663 4.10405 17.1457 4.29 16.96L4.35 16.9C4.58054 16.6643 4.73519 16.365 4.794 16.0406C4.85282 15.7162 4.81312 15.3816 4.68 15.08C4.55324 14.7842 4.34276 14.532 4.07447 14.3543C3.80618 14.1766 3.49179 14.0813 3.17 14.08H3C2.46957 14.08 1.96086 13.8693 1.58579 13.4942C1.21071 13.1191 1 12.6104 1 12.08C1 11.5496 1.21071 11.0409 1.58579 10.6658C1.96086 10.2907 2.46957 10.08 3 10.08H3.09C3.42099 10.0723 3.742 9.96512 4.0113 9.77251C4.28059 9.5799 4.48572 9.31074 4.6 9C4.73312 8.69838 4.77282 8.36381 4.714 8.03941C4.65519 7.71502 4.50054 7.41568 4.27 7.18L4.21 7.12C4.02405 6.93425 3.87653 6.71368 3.77588 6.47088C3.67523 6.22808 3.62343 5.96783 3.62343 5.705C3.62343 5.44217 3.67523 5.18192 3.77588 4.93912C3.87653 4.69632 4.02405 4.47575 4.21 4.29C4.39575 4.10405 4.61632 3.95653 4.85912 3.85588C5.10192 3.75523 5.36217 3.70343 5.625 3.70343C5.88783 3.70343 6.14808 3.75523 6.39088 3.85588C6.63368 3.95653 6.85425 4.10405 7.04 4.29L7.1 4.35C7.33568 4.58054 7.63502 4.73519 7.95941 4.794C8.28381 4.85282 8.61838 4.81312 8.92 4.68H9C9.29577 4.55324 9.54802 4.34276 9.72569 4.07447C9.90337 3.80618 9.99872 3.49179 10 3.17V3C10 2.46957 10.2107 1.96086 10.5858 1.58579C10.9609 1.21071 11.4696 1 12 1C12.5304 1 13.0391 1.21071 13.4142 1.58579C13.7893 1.96086 14 2.46957 14 3V3.09C14.0013 3.41179 14.0966 3.72618 14.2743 3.99447C14.452 4.26276 14.7042 4.47324 15 4.6C15.3016 4.73312 15.6362 4.77282 15.9606 4.714C16.285 4.65519 16.5843 4.50054 16.82 4.27L16.88 4.21C17.0657 4.02405 17.2863 3.87653 17.5291 3.77588C17.7719 3.67523 18.0322 3.62343 18.295 3.62343C18.5578 3.62343 18.8181 3.67523 19.0609 3.77588C19.3037 3.87653 19.5243 4.02405 19.71 4.21C19.896 4.39575 20.0435 4.61632 20.1441 4.85912C20.2448 5.10192 20.2966 5.36217 20.2966 5.625C20.2966 5.88783 20.2448 6.14808 20.1441 6.39088C20.0435 6.63368 19.896 6.85425 19.71 7.04L19.65 7.1C19.4195 7.33568 19.2648 7.63502 19.206 7.95941C19.1472 8.28381 19.1869 8.61838 19.32 8.92V9C19.4468 9.29577 19.6572 9.54802 19.9255 9.72569C20.1938 9.90337 20.5082 9.99872 20.83 10H21C21.5304 10 22.0391 10.2107 22.4142 10.5858C22.7893 10.9609 23 11.4696 23 12C23 12.5304 22.7893 13.0391 22.4142 13.4142C22.0391 13.7893 21.5304 14 21 14H20.91C20.5882 14.0013 20.2738 14.0966 20.0055 14.2743C19.7372 14.452 19.5268 14.7042 19.4 15Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              Tuning Dashboard
            </Link>
            <button 
              onClick={() => {
                localStorage.removeItem('auth_token');
                window.location.href = '/';
              }}
              className="nav-link"
              title="Logout from application"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5m0 0l-5-5m5 5H9" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              Logout
            </button>
          </div>
          <div className="header-content">
            <div className="logo-container">
              <div 
                className="logo"
                onClick={() => {
                  const clicks = parseInt(sessionStorage.getItem('admin_clicks') || '0') + 1;
                  sessionStorage.setItem('admin_clicks', clicks.toString());
                  if (clicks === 3) {
                    window.location.href = '/tuning/auth';
                    sessionStorage.removeItem('admin_clicks');
                  }
                  setTimeout(() => sessionStorage.removeItem('admin_clicks'), 3000);
                }}
                style={{ cursor: 'pointer' }}
                title="Admin access: Click 3 times"
              >
                <Image 
                  src="/dr-chaffee.jpg" 
                  alt="Dr. Anthony Chaffee" 
                  width={80} 
                  height={80}
                  style={{ borderRadius: '50%', objectFit: 'cover' }}
                  priority
                />
              </div>
            </div>
            <h1>Ask Dr. Chaffee</h1>
            <p>Interactive Knowledge Base</p>
            <div className="search-hint">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 16V12M12 8H12.01M22 12C22 17.5228 17.5228 22 12 22C6.47715 22 2 17.5228 2 12C2 6.47715 6.47715 2 12 2C17.5228 2 22 6.47715 22 12Z" 
                  stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
              <span>
                <strong>How it works:</strong> Enter your question and get AI-generated answers based on Anthony Chaffee's content, with direct links to video clips.
              </span>
            </div>
          </div>
          <div className={`topics-container ${isSearching ? 'disabled' : ''}`}>
            <div className="topics-title">Popular topics:</div>
            <div className="topics">
              <button 
                onClick={() => !isSearching && setQuery('carnivore diet benefits')}
                disabled={isSearching}
                aria-disabled={isSearching}
              >Carnivore Diet</button>
              <button 
                onClick={() => !isSearching && setQuery('autoimmune conditions treatment')}
                disabled={isSearching}
                aria-disabled={isSearching}
              >Autoimmune Conditions</button>
              <button 
                onClick={() => !isSearching && setQuery('ketosis explained')}
                disabled={isSearching}
                aria-disabled={isSearching}
              >Ketosis</button>
              <button 
                onClick={() => !isSearching && setQuery('plant toxins in food')}
                disabled={isSearching}
                aria-disabled={isSearching}
              >Plant Toxins</button>
              <button 
                onClick={() => !isSearching && setQuery('mental health and depression')}
                disabled={isSearching}
                aria-disabled={isSearching}
              >Mental Health</button>
            </div>
          </div>
        </div>

        <DisclaimerBanner />

        <ErrorBoundary>
          <SearchBar 
            query={query} 
            setQuery={handleSetQuery} 
            handleSearch={handleSearch} 
            loading={loading}
            answerStyle={answerStyle}
            onAnswerStyleChange={setAnswerStyle}
            disabled={isSearching}
          />
        </ErrorBoundary>

        <ErrorBoundary>
          <FilterPills 
            sourceFilter={sourceFilter} 
            setSourceFilter={setSourceFilter} 
            yearFilter={yearFilter} 
            setYearFilter={setYearFilter} 
            availableYears={availableYears}
            disabled={isSearching}
          />
        </ErrorBoundary>

        {error && (
          <div className="error-message" role="alert">
            ⚠️ {error}
          </div>
        )}

        <ErrorBoundary>
          <Suspense fallback={loading ? <LoadingSkeleton /> : <LazyLoadFallback />}>
            <AnswerCard
              answer={answerData}
              loading={answerLoading}
              error={answerError}
              onPlayClip={(videoId, timestamp) => seekToTimestamp(videoId, timestamp)}
              onCopyLink={copyTimestampLink}
              onCancel={handleCancelAnswer}
              answerStyle={answerStyle}
              onStyleChange={async (newStyle) => {
                console.log(`🔄 Switching answer style from ${answerStyle} to ${newStyle}`);
                setAnswerStyle(newStyle);
                // Clear current answer to show loading
                setAnswerData(null);
                // Re-fetch answer with new style (pass as parameter to avoid stale closure)
                if (query && !answerLoading) {
                  console.log(`📡 Re-fetching answer with style: ${newStyle}`);
                  performAnswerWithRetry(query, 5, newStyle);
                }
              }}
            />
          </Suspense>
        </ErrorBoundary>

        {/* Show search results when answer is ready or when cancelled */}
        {((answerData && !answerLoading) || answerCancelled) && (
          <ErrorBoundary>
            <Suspense fallback={loading ? <LoadingSkeleton /> : <LazyLoadFallback />}>
              <div className="supporting-clips-section">
                <h2>{answerCancelled ? "Search Results" : "Supporting Video Clips"}</h2>
                <p className="supporting-clips-info">
                  {answerCancelled 
                    ? "Here are the search results for your query." 
                    : "These clips were used to generate the answer above."}
                </p>
                <SearchResults 
                  results={results}
                  query={query}
                  loading={loading}
                  totalResults={totalResults}
                  groupedResults={groupedResults}
                  sourceFilter={sourceFilter}
                  highlightSearchTerms={highlightSearchTerms}
                  seekToTimestamp={seekToTimestamp}
                  copyTimestampLink={copyTimestampLink}
                />
              </div>
            </Suspense>
          </ErrorBoundary>
        )}

        <Footer />

        {showCopyNotification && (
          <div className="copy-notification">
            {copySuccess}
          </div>
        )}
        
        <DarkModeToggle />

        <style jsx>{`
          /* Main container - centered layout with consistent padding */
          .container {
            max-width: 1000px;
            margin: 0 auto;
            padding: 1.5rem 1.25rem 2.5rem;
            width: 100%;
            box-sizing: border-box;
          }
          
          @media (min-width: 1024px) {
            .container {
              max-width: 1100px;
              padding: 2rem 2.5rem 3rem;
            }
          }
          
          .header {
            text-align: center;
            margin-bottom: var(--space-6);
            padding: var(--space-6) 0;
            position: relative;
          }
          
          .header-top-bar {
            display: flex;
            justify-content: flex-end;
            max-width: 1200px;
            margin: 0 auto var(--space-4) auto;
          }
          
          .nav-link {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 0.4rem;
            padding: 0.5rem 0.75rem;
            background: transparent;
            border: none;
            font-size: 0.875rem;
            font-weight: 500;
            cursor: pointer;
            transition: color 0.2s ease, text-decoration 0.2s ease;
          }
          
          .nav-link svg {
            display: block;
            width: 16px;
            height: 16px;
            flex-shrink: 0;
          }
          
          .header-content {
            max-width: 800px;
            margin: 0 auto var(--space-6) auto;
          }
          
          .logo-container {
            margin-bottom: var(--space-4);
            display: flex;
            justify-content: center;
          }
          
          .logo {
            width: 80px;
            height: 80px;
            min-width: 80px;
            min-height: 80px;
            background: linear-gradient(135deg, var(--color-primary), var(--color-accent));
            color: white;
            border-radius: 999px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 2rem;
            font-weight: 700;
            box-shadow: var(--shadow-md);
            position: relative;
            overflow: hidden;
            flex-shrink: 0;
            aspect-ratio: 1 / 1;
          }
          
          .logo::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: radial-gradient(circle at 30% 30%, rgba(255,255,255,0.3) 0%, rgba(255,255,255,0) 70%);
          }
          
          .header h1 {
            font-size: 2.8rem;
            margin-bottom: var(--space-3);
            color: var(--color-text);
            font-weight: 800;
            background: linear-gradient(to right, var(--color-primary), var(--color-accent));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            text-fill-color: transparent;
          }
          
          .header p {
            font-size: 1.3rem;
            color: var(--color-text-light);
            margin-bottom: var(--space-5);
          }

          .search-hint {
            background-color: var(--color-card);
            border: 1px solid var(--color-border);
            border-radius: var(--radius-xl);
            padding: var(--space-4) var(--space-5);
            font-size: 0.95rem;
            color: var(--color-text);
            text-align: left;
            display: flex;
            flex-direction: row;
            align-items: flex-start;
            gap: var(--space-3);
            box-shadow: var(--shadow-sm);
            max-width: 640px;
            margin: 0 auto;
          }

          .search-hint svg {
            flex-shrink: 0;
            margin-top: 3px;
            color: var(--color-text-muted);
            width: 20px;
            height: 20px;
          }

          .search-hint span {
            line-height: 1.5;
            text-align: left;
          }

          .search-hint strong {
            color: var(--color-text);
            font-weight: 600;
          }
          
          .topics-container {
            margin-top: var(--space-6);
            padding-top: var(--space-4);
          }
          
          .topics-title {
            font-size: 1rem;
            color: var(--color-text-light);
            margin-bottom: var(--space-3);
            font-weight: 500;
          }
          
          .topics {
            display: flex;
            flex-wrap: wrap;
            gap: var(--space-2);
            justify-content: center;
          }
          
          .topics button {
            background: var(--color-card);
            border: 1px solid var(--color-border);
            border-radius: var(--radius-lg);
            padding: var(--space-2) var(--space-3);
            font-size: 0.9rem;
            color: var(--color-text);
            cursor: pointer;
            transition: all var(--transition-normal);
          }
          
          .topics button:hover:not(:disabled) {
            background: rgba(59, 130, 246, 0.1);
            border-color: var(--color-primary-light);
            transform: translateY(-1px);
          }
          
          .topics button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
          }
          
          .topics-container.disabled {
            pointer-events: none;
          }
          
          @media (max-width: 768px) {
            .container {
              padding: var(--space-4);
              max-width: 100%;
              overflow-x: hidden;
            }

            .header {
              padding: var(--space-4) 0;
              margin-bottom: var(--space-4);
            }
            
            .header-top-bar {
              margin-bottom: var(--space-3);
              flex-wrap: wrap;
              gap: var(--space-2);
            }
            
            .nav-link {
              padding: 0.375rem 0.5rem;
              font-size: 0.8rem;
            }
            
            .nav-link svg {
              width: 14px;
              height: 14px;
            }

            .header-content {
              padding: 0;
            }

            .logo-container {
              margin-bottom: var(--space-3);
            }

            .header h1 {
              font-size: 1.875rem;
              margin-bottom: var(--space-2);
            }
            
            .header p {
              font-size: 1rem;
              margin-bottom: var(--space-3);
            }

            .search-hint {
              padding: var(--space-3);
              font-size: 0.875rem;
              margin: 0;
            }

            .search-hint svg {
              width: 18px;
              height: 18px;
            }

            .topics-container {
              margin-top: var(--space-4);
              padding: 0;
            }
            
            .topics {
              gap: var(--space-2);
            }
            
            .topics button {
              font-size: 0.8rem;
              padding: var(--space-2) var(--space-3);
            }

            .supporting-clips-section h2 {
              font-size: 1.25rem;
            }

            .copy-notification {
              bottom: 1rem;
              right: 1rem;
              left: 1rem;
              padding: 0.75rem 1rem;
              font-size: 0.875rem;
            }
          }

          @media (max-width: 480px) {
            .container {
              padding: var(--space-3);
            }

            .header {
              padding: var(--space-3) 0;
              margin-bottom: var(--space-3);
            }
            
            .header-top-bar {
              justify-content: center;
              margin-bottom: var(--space-3);
            }
            
            .nav-link {
              padding: 0.25rem 0.375rem;
              font-size: 0.75rem;
            }

            .header-content {
              padding: 0;
            }

            .logo {
              width: 60px;
              height: 60px;
              min-width: 60px;
              min-height: 60px;
            }

            .logo-container {
              margin-bottom: var(--space-2);
            }

            .header h1 {
              font-size: 1.5rem;
              margin-bottom: var(--space-1);
            }

            .header p {
              font-size: 0.9rem;
              margin-bottom: var(--space-3);
            }

            .search-hint {
              flex-direction: row;
              text-align: left;
              gap: var(--space-2);
              padding: var(--space-3);
              margin: 0 auto;
              font-size: 0.8125rem;
            }
            
            .search-hint svg {
              width: 16px;
              height: 16px;
              margin-top: 2px;
            }

            .topics-container {
              margin-top: var(--space-3);
              padding: 0;
            }

            .topics-title {
              font-size: 0.8125rem;
              margin-bottom: var(--space-2);
            }

            .topics {
              gap: 0.375rem;
            }

            .topics button {
              font-size: 0.75rem;
              padding: 0.375rem 0.625rem;
            }

            .supporting-clips-section {
              margin-top: var(--space-5);
              padding-top: var(--space-3);
            }

            .supporting-clips-section h2 {
              font-size: 1.125rem;
            }

            .supporting-clips-info {
              font-size: 0.8125rem;
            }
          }
          
          .error-message {
            background-color: var(--color-card);
            border: 1px solid #ef4444;
            color: #ef4444;
            padding: 1rem;
            border-radius: var(--radius-lg);
            margin: 1rem auto;
            max-width: 640px;
          }
          
          :global(.dark-mode) .error-message {
            background-color: rgba(239, 68, 68, 0.1);
            color: #f87171;
          }
          
          .copy-notification {
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            background-color: #2d3748;
            color: white;
            padding: 0.75rem 1.5rem;
            border-radius: 0.5rem;
            animation: fadeIn 0.3s, fadeOut 0.3s 1.7s;
            z-index: 1000;
          }
          
          @keyframes fadeIn {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
          }
          
          @keyframes fadeOut {
            from { opacity: 1; transform: translateY(0); }
            to { opacity: 0; transform: translateY(20px); }
          }
          
          .lazy-load-placeholder {
            min-height: 200px;
            width: 100%;
            background: linear-gradient(90deg, var(--color-background), var(--color-border-light), var(--color-background));
            background-size: 200% 100%;
            animation: shimmer 2s infinite;
            border-radius: var(--radius-xl);
          }
          
          @keyframes shimmer {
            0% { background-position: -200% 0; }
            100% { background-position: 200% 0; }
          }
          
          .supporting-clips-section {
            margin-top: var(--space-8);
            padding-top: var(--space-6);
            border-top: 1px solid var(--color-border);
          }
          
          .supporting-clips-section h2 {
            font-size: 1.5rem;
            margin-bottom: var(--space-2);
            color: var(--color-text);
          }
          
          .supporting-clips-info {
            color: var(--color-text-light);
            margin-bottom: var(--space-4);
            font-size: 0.95rem;
          }
        `}</style>
      </main>
    </>
  );
}
