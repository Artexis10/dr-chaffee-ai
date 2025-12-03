'use client';

import { useState, useEffect } from 'react';
import { Save, Loader2, AlertTriangle, CheckCircle, AlertCircle, Info, RefreshCw } from 'lucide-react';
import '../tuning-pages.css';
import { useSearchConfig, invalidateTuningCache, type SearchConfig, type SearchConfigResponse } from '@/hooks/useTuningData';
import { apiFetch } from '@/utils/api';

const DEFAULT_CONFIG: SearchConfig = {
  top_k: 100,
  min_similarity: 0.3,
  enable_reranker: false,
  rerank_top_k: 200,
  return_top_k: 20,
};

export default function SearchPage() {
  const { data: configData, loading, error: loadError, refresh: refreshConfig } = useSearchConfig();
  const [config, setConfig] = useState<SearchConfig>(DEFAULT_CONFIG);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState<'success' | 'error' | 'warning' | 'info'>('success');
  const [dbError, setDbError] = useState<string | null>(null);
  const [testQuery, setTestQuery] = useState('');
  const [testResults, setTestResults] = useState<any>(null);
  const [testing, setTesting] = useState(false);

  // Sync config from hook
  useEffect(() => {
    if (configData?.config) {
      setConfig(configData.config);
    }
    if (configData?.error) {
      setDbError(configData.error);
      if (configData.error_code === 'MIGRATION_REQUIRED') {
        setMessage('Using default search settings. Database storage is not configured.');
        setMessageType('info');
      }
    }
  }, [configData]);

  // Show error from hook
  useEffect(() => {
    if (loadError) {
      setMessage('Could not connect to backend. Using default values.');
      setMessageType('error');
    }
  }, [loadError]);

  const handleSave = async () => {
    setSaving(true);
    setMessage('');
    
    try {
      const res = await apiFetch('/api/tuning/search-config', {
        method: 'PUT',
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
          invalidateTuningCache('search-config');
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
      const res = await apiFetch('/api/search', {
        method: 'POST',
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
      <div className="tuning-page tuning-centered">
        <p className="tuning-text-muted">Loading configuration...</p>
      </div>
    );
  }

  const getAlertClass = () => {
    switch (messageType) {
      case 'success': return 'tuning-alert-success';
      case 'error': return 'tuning-alert-error';
      case 'warning': return 'tuning-alert-warning';
      case 'info': return 'tuning-alert-info';
      default: return '';
    }
  };

  const getMessageIcon = () => {
    const style = { width: 20, height: 20 };
    switch (messageType) {
      case 'success': return <CheckCircle style={style} />;
      case 'error': return <AlertCircle style={style} />;
      case 'warning': return <AlertTriangle style={style} />;
      case 'info': return <Info style={style} />;
      default: return null;
    }
  };

  return (
    <div className="tuning-page">
      {/* Header */}
      <div className="tuning-header">
        <div>
          <h1 className="tuning-title">Search Configuration</h1>
          <p className="tuning-text-muted">Tune search parameters and test queries</p>
        </div>
        <button 
          onClick={() => refreshConfig()} 
          className="tuning-btn tuning-btn-secondary"
          title="Refresh configuration"
          disabled={loading}
        >
          <RefreshCw style={{ width: 16, height: 16 }} />
        </button>
      </div>

      {/* Info Banner for migration status */}
      {dbError && (
        <div className="tuning-alert tuning-alert-warning">
          <AlertTriangle style={{ width: 20, height: 20, flexShrink: 0, marginTop: 2 }} />
          <div>
            <p style={{ fontWeight: 600, marginBottom: 4 }}>Database Migration Required</p>
            <p style={{ fontSize: '0.875rem', opacity: 0.9, margin: 0 }}>
              Search settings are working but won't persist between server restarts. 
              Run <code style={{ background: 'rgba(0,0,0,0.1)', padding: '0.125rem 0.25rem', borderRadius: '0.25rem' }}>alembic upgrade head</code> to enable persistence.
            </p>
          </div>
        </div>
      )}

      {/* Message */}
      {message && !dbError && (
        <div className={`tuning-alert ${getAlertClass()}`}>
          {getMessageIcon()}
          {message}
        </div>
      )}

      <div className="tuning-grid-2">
        {/* Configuration Panel */}
        <div className="tuning-card">
          <h2 className="tuning-card-title">Parameters</h2>

          <div className="tuning-form-group">
            <label className="tuning-label">Initial results to consider</label>
            <input
              type="number"
              value={config.top_k}
              onChange={(e) => setConfig({ ...config, top_k: parseInt(e.target.value) || 100 })}
              className="tuning-input"
            />
            <p className="tuning-hint">How many clips to look at before ranking them.</p>
          </div>

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
            <p className="tuning-hint">Only show clips at least this relevant (0-1).</p>
          </div>

          <div className="tuning-form-group">
            <label className="tuning-checkbox-label">
              <input
                type="checkbox"
                checked={config.enable_reranker}
                onChange={(e) => setConfig({ ...config, enable_reranker: e.target.checked })}
                className="tuning-checkbox"
              />
              <span className="tuning-label" style={{ marginBottom: 0 }}>
                Use extra AI step to improve ranking
              </span>
            </label>
            <p className="tuning-hint" style={{ marginLeft: '2rem' }}>More accurate but slower.</p>
          </div>

          {config.enable_reranker && (
            <div className="tuning-form-group">
              <label className="tuning-label">Results to rerank</label>
              <input
                type="number"
                value={config.rerank_top_k}
                onChange={(e) => setConfig({ ...config, rerank_top_k: parseInt(e.target.value) || 200 })}
                className="tuning-input"
              />
            </div>
          )}

          <div className="tuning-form-group">
            <label className="tuning-label">Number of clips to use in answer</label>
            <input
              type="number"
              value={config.return_top_k}
              onChange={(e) => setConfig({ ...config, return_top_k: parseInt(e.target.value) || 20 })}
              className="tuning-input"
            />
          </div>

          <button
            onClick={handleSave}
            disabled={saving}
            className="tuning-btn tuning-btn-primary"
            style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', marginTop: '0.5rem' }}
          >
            {saving ? (
              <>
                <Loader2 style={{ width: 16, height: 16 }} className="tuning-spinner" />
                Saving...
              </>
            ) : (
              <>
                <Save style={{ width: 16, height: 16 }} />
                Save Configuration
              </>
            )}
          </button>
        </div>

        {/* Test Panel */}
        <div className="tuning-card">
          <h2 className="tuning-card-title">Test Search</h2>

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
            style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}
          >
            {testing ? (
              <>
                <Loader2 style={{ width: 16, height: 16 }} className="tuning-spinner" />
                Testing...
              </>
            ) : (
              'Test Search'
            )}
          </button>

          {testResults && (
            <div className="tuning-results">
              <h3 className="tuning-label" style={{ marginBottom: '0.75rem' }}>
                Results ({testResults.results?.length || 0})
              </h3>
              <div style={{ maxHeight: 300, overflowY: 'auto' }}>
                {testResults.results?.map((result: any, idx: number) => (
                  <div key={idx} className="tuning-result-item">
                    <p className="tuning-hint" style={{ marginBottom: '0.25rem' }}>
                      Score: {result.score?.toFixed(3)}
                    </p>
                    <p style={{ fontSize: '0.875rem', color: 'var(--text-primary)' }}>
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
  );
}
