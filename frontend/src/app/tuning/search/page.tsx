'use client';

import { useState, useEffect } from 'react';
import { Save, Loader2, AlertTriangle, CheckCircle, AlertCircle, Info } from 'lucide-react';

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
  const [messageType, setMessageType] = useState<'success' | 'error' | 'warning' | 'info'>('success');
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
            // Don't show as error - just info that we're using defaults
            setMessage('Using default search settings. Database storage is not configured.');
            setMessageType('info');
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
          if (data.error_code === 'MIGRATION_REQUIRED') {
            // Settings work at runtime, just can't persist
            setMessageType('info');
            setMessage('Settings applied for this session. Database storage is not configured, so settings will reset on server restart.');
          } else {
            setMessageType('warning');
            setMessage(data.error);
          }
        } else {
          setDbError(null);
          setMessageType('success');
          setMessage('Configuration saved successfully');
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
      <div className="tuning-page">
        <div className="tuning-loading">Loading configuration...</div>
      </div>
    );
  }

  const getMessageIcon = () => {
    switch (messageType) {
      case 'success': return <CheckCircle />;
      case 'error': return <AlertCircle />;
      case 'warning': return <AlertTriangle />;
      case 'info': return <Info />;
      default: return null;
    }
  };

  return (
    <div className="tuning-page">
      {/* Header */}
      <div className="tuning-page-header">
        <h1 className="tuning-page-title">Search Configuration</h1>
        <p className="tuning-page-description">
          Tune search parameters and test queries
        </p>
      </div>

      {/* Info Banner for migration status */}
      {dbError && (
        <div className="tuning-message tuning-message-info" style={{ marginBottom: '1.5rem', alignItems: 'flex-start' }}>
          <Info style={{ flexShrink: 0, marginTop: '0.125rem' }} />
          <div>
            <p style={{ fontWeight: 600, marginBottom: '0.25rem' }}>Using Default Settings</p>
            <p style={{ opacity: 0.9 }}>
              Search settings are working but won't persist between server restarts. 
              This is fine for testing. For permanent settings, ask your developer to run the database migration.
            </p>
          </div>
        </div>
      )}

      {/* Message */}
      {message && !dbError && (
        <div className={`tuning-message tuning-message-${messageType}`}>
          {getMessageIcon()}
          {message}
        </div>
      )}

      <div className="tuning-two-col">
        {/* Configuration Panel */}
        <div className="tuning-card">
          <h2 className="tuning-card-title" style={{ marginBottom: '1.5rem' }}>
            Parameters
          </h2>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            {/* top_k */}
            <div className="tuning-form-group">
              <label className="tuning-label">Initial results to consider</label>
              <input
                type="number"
                value={config.top_k}
                onChange={(e) => setConfig({ ...config, top_k: parseInt(e.target.value) || 100 })}
                className="tuning-input"
              />
              <p className="tuning-input-hint">
                How many clips to look at before ranking them. Higher = more accurate but slightly slower.
              </p>
            </div>

            {/* min_score */}
            <div className="tuning-form-group">
              <label className="tuning-label">Minimum relevance</label>
              <input
                type="number"
                step="0.01"
                min="0"
                max="1"
                value={config.min_similarity}
                onChange={(e) => setConfig({ ...config, min_similarity: parseFloat(e.target.value) || 0 })}
                className="tuning-input"
              />
              <p className="tuning-input-hint">
                Only show clips that are at least this relevant to the question (0-1).
              </p>
            </div>

            {/* enable_reranker */}
            <div className="tuning-form-group">
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={config.enable_reranker}
                  onChange={(e) => setConfig({ ...config, enable_reranker: e.target.checked })}
                  style={{ width: '1.25rem', height: '1.25rem', cursor: 'pointer' }}
                />
                <span className="tuning-label" style={{ marginBottom: 0 }}>
                  Use extra AI step to improve ranking
                </span>
              </label>
              <p className="tuning-input-hint" style={{ marginTop: '0.5rem' }}>
                More accurate ordering of clips, but a bit slower and may cost more if using paid models.
              </p>
            </div>

            {/* rerank_top_k */}
            {config.enable_reranker && (
              <div className="tuning-form-group">
                <label className="tuning-label">Results to rerank</label>
                <input
                  type="number"
                  value={config.rerank_top_k}
                  onChange={(e) => setConfig({ ...config, rerank_top_k: parseInt(e.target.value) || 200 })}
                  className="tuning-input"
                />
                <p className="tuning-input-hint">
                  How many results to pass through the extra ranking step.
                </p>
              </div>
            )}

            {/* return_top_k */}
            <div className="tuning-form-group">
              <label className="tuning-label">Number of clips to use in answer</label>
              <input
                type="number"
                value={config.return_top_k}
                onChange={(e) => setConfig({ ...config, return_top_k: parseInt(e.target.value) || 20 })}
                className="tuning-input"
              />
              <p className="tuning-input-hint">
                How many top clips the AI uses when building an answer.
              </p>
            </div>

            {/* Save Button */}
            <button
              onClick={handleSave}
              disabled={saving}
              className="tuning-btn tuning-btn-primary"
              style={{ marginTop: '0.5rem' }}
            >
              {saving ? (
                <>
                  <Loader2 className="tuning-spinner" style={{ width: '1rem', height: '1rem' }} />
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
        <div className="tuning-card">
          <h2 className="tuning-card-title" style={{ marginBottom: '1.5rem' }}>
            Test Search
          </h2>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div className="tuning-form-group">
              <label className="tuning-label">Query</label>
              <input
                type="text"
                value={testQuery}
                onChange={(e) => setTestQuery(e.target.value)}
                placeholder="Enter a search query..."
                className="tuning-input"
              />
            </div>

            <button
              onClick={handleTestSearch}
              disabled={testing}
              className="tuning-btn tuning-btn-secondary"
            >
              {testing ? (
                <>
                  <Loader2 className="tuning-spinner" style={{ width: '1rem', height: '1rem' }} />
                  Testing...
                </>
              ) : (
                'Test Search'
              )}
            </button>

            {testResults && (
              <div style={{
                background: 'var(--bg-card-elevated, #f3f4f6)',
                borderRadius: '0.5rem',
                padding: '1rem',
                marginTop: '0.5rem'
              }}>
                <h3 className="tuning-label" style={{ marginBottom: '0.75rem' }}>
                  Results ({testResults.results?.length || 0})
                </h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', maxHeight: '300px', overflowY: 'auto' }}>
                  {testResults.results?.map((result: any, idx: number) => (
                    <div key={idx} style={{
                      background: 'var(--bg-card, white)',
                      padding: '0.75rem',
                      borderRadius: '0.375rem',
                      borderLeft: '3px solid var(--accent, #000000)'
                    }}>
                      <p className="tuning-input-hint" style={{ marginBottom: '0.25rem' }}>
                        Score: {result.score?.toFixed(3)}
                      </p>
                      <p style={{ fontSize: '0.875rem', lineHeight: '1.4' }}>
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
