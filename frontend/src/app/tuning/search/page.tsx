'use client';

import { useState, useEffect } from 'react';
import { Save, Loader2, RefreshCw, AlertTriangle } from 'lucide-react';

interface SearchConfig {
  top_k: number;
  min_similarity: number;
  enable_reranker: boolean;
  rerank_top_k: number;
  return_top_k: number;
}

interface SearchConfigResponse {
  config: SearchConfig | null;
  error: string | null;
  error_code: string | null;
}

export default function SearchPage() {
  const [config, setConfig] = useState<SearchConfig>({
    top_k: 100,
    min_similarity: 0.3,
    enable_reranker: false,
    rerank_top_k: 200,
    return_top_k: 20,
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState<'success' | 'error' | 'warning'>('success');
  const [dbError, setDbError] = useState<string | null>(null);
  const [testQuery, setTestQuery] = useState('');
  const [testResults, setTestResults] = useState<any>(null);
  const [testing, setTesting] = useState(false);

  useEffect(() => {
    loadConfig();
  }, []);

  const loadConfig = async () => {
    setLoading(true);
    setDbError(null);
    try {
      const res = await fetch('/api/tuning/search-config');
      if (res.ok) {
        const data: SearchConfigResponse = await res.json();
        if (data.config) {
          setConfig(data.config);
        }
        if (data.error) {
          setDbError(data.error);
          if (data.error_code === 'MIGRATION_REQUIRED') {
            setMessage('Database migration required - using default values');
            setMessageType('warning');
          }
        }
      } else if (res.status === 401) {
        setMessage('Please authenticate to access search configuration');
        setMessageType('error');
      } else {
        console.warn('Failed to load config from backend, using defaults');
      }
    } catch (error) {
      console.warn('Failed to load config from backend:', error);
      setMessage('Could not connect to backend. Using default values.');
      setMessageType('error');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setMessage('');
    
    try {
      const res = await fetch('/api/tuning/search-config', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config)
      });
      
      if (res.ok) {
        const data: SearchConfigResponse = await res.json();
        if (data.config) {
          setConfig(data.config);
        }
        if (data.error) {
          setDbError(data.error);
          setMessageType('warning');
          setMessage(data.error_code === 'MIGRATION_REQUIRED' 
            ? 'Configuration could not be saved - database migration required'
            : data.error);
        } else {
          setDbError(null);
          setMessageType('success');
          setMessage('Configuration saved to database');
          setTimeout(() => setMessage(''), 3000);
        }
      } else if (res.status === 401) {
        setMessageType('error');
        setMessage('Authentication required. Please log in again.');
      } else {
        const error = await res.json();
        throw new Error(error.detail || 'Failed to save');
      }
    } catch (error: any) {
      console.error('Error saving config:', error);
      setMessageType('error');
      setMessage(error.message || 'Failed to save configuration. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  const handleTestSearch = async () => {
    if (!testQuery.trim()) {
      setMessage('Please enter a search query');
      return;
    }

    setTesting(true);
    try {
      setMessage('');
      const res = await fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: testQuery,
          top_k: config.top_k,
          min_similarity: config.min_similarity,
          enable_reranker: config.enable_reranker,
          rerank_top_k: config.rerank_top_k,
          return_top_k: config.return_top_k
        })
      });

      if (res.ok) {
        const data = await res.json();
        setTestResults(data);
      } else {
        setMessage('Search test failed');
      }
    } catch (error) {
      console.error('Error testing search:', error);
      setMessage('Error testing search');
    } finally {
      setTesting(false);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <p style={{ color: '#6b7280' }}>Loading configuration...</p>
      </div>
    );
  }

  return (
    <div style={{ padding: '2rem' }}>
      {/* Header */}
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '2rem', fontWeight: 700, color: '#1f2937', marginBottom: '0.5rem' }}>
          Search Configuration
        </h1>
        <p style={{ color: '#6b7280' }}>
          Tune search parameters and test queries
        </p>
      </div>

      {/* Database Migration Warning Banner */}
      {dbError && (
        <div style={{
          background: '#fffbeb',
          color: '#92400e',
          padding: '1rem 1.25rem',
          borderRadius: '0.5rem',
          marginBottom: '1.5rem',
          border: '1px solid #fcd34d',
          fontSize: '0.875rem',
          display: 'flex',
          alignItems: 'flex-start',
          gap: '0.75rem'
        }}>
          <AlertTriangle style={{ width: '1.25rem', height: '1.25rem', flexShrink: 0, marginTop: '0.125rem' }} />
          <div>
            <p style={{ fontWeight: 600, marginBottom: '0.25rem' }}>Database Migration Required</p>
            <p style={{ color: '#a16207' }}>
              Search configuration could not be saved — the database migration for search_config must be applied.
              Please run migration 015_search_config.sql on your database.
            </p>
          </div>
        </div>
      )}

      {/* Message */}
      {message && !dbError && (
        <div style={{
          background: messageType === 'success' ? '#f0fdf4' : messageType === 'warning' ? '#fffbeb' : '#fef2f2',
          color: messageType === 'success' ? '#059669' : messageType === 'warning' ? '#92400e' : '#dc2626',
          padding: '0.75rem 1rem',
          borderRadius: '0.5rem',
          marginBottom: '1.5rem',
          border: `1px solid ${messageType === 'success' ? '#d1fae5' : messageType === 'warning' ? '#fcd34d' : '#fecaca'}`,
          fontSize: '0.875rem',
          fontWeight: 500,
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem'
        }}>
          {messageType === 'success' ? '✓' : '⚠'} {message}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
        {/* Configuration Panel */}
        <div style={{
          background: 'white',
          border: '1px solid #e5e7eb',
          borderRadius: '0.75rem',
          padding: '1.5rem'
        }}>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#1f2937', marginBottom: '1.5rem' }}>
            Parameters
          </h2>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            {/* top_k */}
            <div>
              <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, color: '#374151', marginBottom: '0.5rem' }}>
                Initial results to consider
              </label>
              <input
                type="number"
                value={config.top_k}
                onChange={(e) => setConfig({ ...config, top_k: parseInt(e.target.value) })}
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '0.5rem',
                  fontSize: '1rem'
                }}
              />
              <p style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: '0.25rem' }}>
                How many clips to look at before ranking them. Higher = more accurate but slightly slower.
              </p>
            </div>

            {/* min_score */}
            <div>
              <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, color: '#374151', marginBottom: '0.5rem' }}>
                Minimum relevance
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                max="1"
                value={config.min_similarity}
                onChange={(e) => setConfig({ ...config, min_similarity: parseFloat(e.target.value) })}
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '0.5rem',
                  fontSize: '1rem'
                }}
              />
              <p style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: '0.25rem' }}>
                Only show clips that are at least this relevant to the question (0-1).
              </p>
            </div>

            {/* enable_reranker */}
            <div>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={config.enable_reranker}
                  onChange={(e) => setConfig({ ...config, enable_reranker: e.target.checked })}
                  style={{ width: '1rem', height: '1rem', cursor: 'pointer' }}
                />
                <span style={{ fontSize: '0.875rem', fontWeight: 600, color: '#374151' }}>
                  Use extra AI step to improve ranking
                </span>
              </label>
              <p style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: '0.5rem' }}>
                More accurate ordering of clips, but a bit slower and may cost more if using paid models.
              </p>
            </div>

            {/* rerank_top_k */}
            {config.enable_reranker && (
              <div>
                <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, color: '#374151', marginBottom: '0.5rem' }}>
                  Results to rerank
                </label>
                <input
                  type="number"
                  value={config.rerank_top_k}
                  onChange={(e) => setConfig({ ...config, rerank_top_k: parseInt(e.target.value) })}
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    border: '1px solid #d1d5db',
                    borderRadius: '0.5rem',
                    fontSize: '1rem'
                  }}
                />
                <p style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: '0.25rem' }}>
                  How many results to pass through the extra ranking step.
                </p>
              </div>
            )}

            {/* return_top_k */}
            <div>
              <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, color: '#374151', marginBottom: '0.5rem' }}>
                Number of clips to use in answer
              </label>
              <input
                type="number"
                value={config.return_top_k}
                onChange={(e) => setConfig({ ...config, return_top_k: parseInt(e.target.value) })}
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '0.5rem',
                  fontSize: '1rem'
                }}
              />
              <p style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: '0.25rem' }}>
                How many top clips the AI uses when building an answer.
              </p>
            </div>

            {/* Save Button */}
            <button
              onClick={handleSave}
              disabled={saving}
              style={{
                padding: '0.75rem 1.5rem',
                background: saving ? '#6b7280' : 'var(--accent, #000000)',
                color: 'white',
                border: 'none',
                borderRadius: '0.5rem',
                fontWeight: 600,
                cursor: saving ? 'not-allowed' : 'pointer',
                transition: 'background 0.2s',
                marginTop: '1rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '0.5rem'
              }}
              onMouseEnter={(e) => {
                if (!saving) e.currentTarget.style.background = 'var(--accent-hover, #333333)';
              }}
              onMouseLeave={(e) => {
                if (!saving) e.currentTarget.style.background = 'var(--accent, #000000)';
              }}
            >
              {saving ? (
                <>
                  <Loader2 style={{ width: '1rem', height: '1rem', animation: 'spin 1s linear infinite' }} />
                  Saving...
                </>
              ) : (
                <>
                  <Save style={{ width: '1rem', height: '1rem' }} />
                  Save Configuration
                </>
              )}
            </button>
          </div>
        </div>

        {/* Test Panel */}
        <div style={{
          background: 'white',
          border: '1px solid #e5e7eb',
          borderRadius: '0.75rem',
          padding: '1.5rem'
        }}>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: '#1f2937', marginBottom: '1.5rem' }}>
            Test Search
          </h2>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, color: '#374151', marginBottom: '0.5rem' }}>
                Query
              </label>
              <input
                type="text"
                value={testQuery}
                onChange={(e) => setTestQuery(e.target.value)}
                placeholder="Enter a search query..."
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '1px solid #d1d5db',
                  borderRadius: '0.5rem',
                  fontSize: '1rem'
                }}
              />
            </div>

            <button
              onClick={handleTestSearch}
              disabled={testing}
              style={{
                padding: '0.75rem 1.5rem',
                background: '#333333',
                color: 'white',
                border: 'none',
                borderRadius: '0.5rem',
                fontWeight: 600,
                cursor: testing ? 'not-allowed' : 'pointer',
                transition: 'background 0.2s',
                opacity: testing ? 0.7 : 1
              }}
              onMouseEnter={(e) => {
                if (!testing) e.currentTarget.style.background = '#555555';
              }}
              onMouseLeave={(e) => {
                if (!testing) e.currentTarget.style.background = '#333333';
              }}
            >
              {testing ? 'Testing...' : 'Test Search'}
            </button>

            {testResults && (
              <div style={{
                background: '#f3f4f6',
                borderRadius: '0.5rem',
                padding: '1rem',
                marginTop: '1rem'
              }}>
                <h3 style={{ fontSize: '0.875rem', fontWeight: 600, color: '#1f2937', marginBottom: '0.75rem' }}>
                  Results ({testResults.results?.length || 0})
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', maxHeight: '300px', overflowY: 'auto' }}>
                  {testResults.results?.map((result: any, idx: number) => (
                    <div key={idx} style={{
                      background: 'white',
                      padding: '0.75rem',
                      borderRadius: '0.375rem',
                      borderLeft: '3px solid #000000'
                    }}>
                      <p style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '0.25rem' }}>
                        Score: {result.score?.toFixed(3)}
                      </p>
                      <p style={{ fontSize: '0.875rem', color: '#1f2937', lineHeight: '1.4' }}>
                        {result.text?.substring(0, 150)}...
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
