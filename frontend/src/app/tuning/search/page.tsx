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
      <div className="p-6 flex items-center justify-center min-h-[300px]">
        <p className="text-gray-500">Loading configuration...</p>
      </div>
    );
  }

  const messageStyles = {
    success: 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400',
    error: 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400',
    warning: 'bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400',
    info: 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400',
  };

  const getMessageIcon = () => {
    switch (messageType) {
      case 'success': return <CheckCircle className="w-5 h-5" />;
      case 'error': return <AlertCircle className="w-5 h-5" />;
      case 'warning': return <AlertTriangle className="w-5 h-5" />;
      case 'info': return <Info className="w-5 h-5" />;
      default: return null;
    }
  };

  return (
    <div className="p-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-1">
          Search Configuration
        </h1>
        <p className="text-gray-500 dark:text-gray-400">
          Tune search parameters and test queries
        </p>
      </div>

      {/* Info Banner for migration status */}
      {dbError && (
        <div className="flex items-start gap-3 p-4 bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400 rounded-lg mb-6">
          <Info className="w-5 h-5 mt-0.5 flex-shrink-0" />
          <div>
            <p className="font-semibold mb-1">Using Default Settings</p>
            <p className="text-sm opacity-90">
              Search settings are working but won't persist between server restarts. 
              This is fine for testing.
            </p>
          </div>
        </div>
      )}

      {/* Message */}
      {message && !dbError && (
        <div className={`flex items-center gap-2 p-4 rounded-lg mb-6 ${messageStyles[messageType]}`}>
          {getMessageIcon()}
          {message}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Configuration Panel */}
        <div className="bg-white dark:bg-neutral-900 border border-gray-200 dark:border-neutral-800 rounded-xl p-5">
          <h2 className="font-semibold text-gray-900 dark:text-white mb-6">Parameters</h2>

          <div className="space-y-5">
            {/* top_k */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                Initial results to consider
              </label>
              <input
                type="number"
                value={config.top_k}
                onChange={(e) => setConfig({ ...config, top_k: parseInt(e.target.value) || 100 })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-black dark:focus:ring-white focus:border-transparent"
              />
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                How many clips to look at before ranking them.
              </p>
            </div>

            {/* min_score */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                Minimum relevance
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                max="1"
                value={config.min_similarity}
                onChange={(e) => setConfig({ ...config, min_similarity: parseFloat(e.target.value) || 0 })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-black dark:focus:ring-white focus:border-transparent"
              />
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                Only show clips at least this relevant (0-1).
              </p>
            </div>

            {/* enable_reranker */}
            <div>
              <label className="flex items-center gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={config.enable_reranker}
                  onChange={(e) => setConfig({ ...config, enable_reranker: e.target.checked })}
                  className="w-5 h-5 rounded border-gray-300 dark:border-neutral-600 text-black dark:text-white focus:ring-black dark:focus:ring-white"
                />
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Use extra AI step to improve ranking
                </span>
              </label>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1.5 ml-8">
                More accurate but slower.
              </p>
            </div>

            {/* rerank_top_k */}
            {config.enable_reranker && (
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                  Results to rerank
                </label>
                <input
                  type="number"
                  value={config.rerank_top_k}
                  onChange={(e) => setConfig({ ...config, rerank_top_k: parseInt(e.target.value) || 200 })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-black dark:focus:ring-white focus:border-transparent"
                />
              </div>
            )}

            {/* return_top_k */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                Number of clips to use in answer
              </label>
              <input
                type="number"
                value={config.return_top_k}
                onChange={(e) => setConfig({ ...config, return_top_k: parseInt(e.target.value) || 20 })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-black dark:focus:ring-white focus:border-transparent"
              />
            </div>

            {/* Save Button */}
            <button
              onClick={handleSave}
              disabled={saving}
              className="w-full py-2.5 px-4 bg-black dark:bg-white text-white dark:text-black font-medium rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50 flex items-center justify-center gap-2 mt-2"
            >
              {saving ? (
                <>
                  <Loader2 className="w-4 h-4 tuning-spinner" />
                  Saving...
                </>
              ) : (
                <>
                  <Save className="w-4 h-4" />
                  Save Configuration
                </>
              )}
            </button>
          </div>
        </div>

        {/* Test Panel */}
        <div className="bg-white dark:bg-neutral-900 border border-gray-200 dark:border-neutral-800 rounded-xl p-5">
          <h2 className="font-semibold text-gray-900 dark:text-white mb-6">Test Search</h2>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                Query
              </label>
              <input
                type="text"
                value={testQuery}
                onChange={(e) => setTestQuery(e.target.value)}
                placeholder="Enter a search query..."
                className="w-full px-3 py-2 border border-gray-300 dark:border-neutral-700 rounded-lg bg-white dark:bg-neutral-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-black dark:focus:ring-white focus:border-transparent"
              />
            </div>

            <button
              onClick={handleTestSearch}
              disabled={testing}
              className="w-full py-2.5 px-4 bg-gray-100 dark:bg-neutral-800 text-gray-900 dark:text-white font-medium rounded-lg hover:bg-gray-200 dark:hover:bg-neutral-700 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
            >
              {testing ? (
                <>
                  <Loader2 className="w-4 h-4 tuning-spinner" />
                  Testing...
                </>
              ) : (
                'Test Search'
              )}
            </button>

            {testResults && (
              <div className="bg-gray-50 dark:bg-neutral-800 rounded-lg p-4 mt-2">
                <h3 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-3">
                  Results ({testResults.results?.length || 0})
                </h3>
                <div className="space-y-3 max-h-[300px] overflow-y-auto">
                  {testResults.results?.map((result: any, idx: number) => (
                    <div key={idx} className="bg-white dark:bg-neutral-900 p-3 rounded-md border-l-3 border-black dark:border-white">
                      <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">
                        Score: {result.score?.toFixed(3)}
                      </p>
                      <p className="text-sm text-gray-700 dark:text-gray-300">
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
