'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Settings, Database, TrendingUp, Zap, Search, DollarSign, LogOut, Home, BarChart3 } from 'lucide-react';
import CustomInstructionsEditor from '../../components/CustomInstructionsEditor';

interface EmbeddingModel {
  key: string;
  provider: string;
  dimensions: number;
  cost_per_1k: number;
  description: string;
  is_active_query: boolean;
}

interface SearchConfig {
  top_k: number;
  min_score: number;
  enable_reranker: boolean;
  rerank_top_k: number;
  return_top_k: number;
}

interface Stats {
  total_videos: number;
  total_segments: number;
  embedding_coverage: string;
  embedding_dimensions: number;
}

export default function TuningPage() {
  const router = useRouter();
  const [models, setModels] = useState<EmbeddingModel[]>([]);
  const [searchConfig, setSearchConfig] = useState<SearchConfig>({
    top_k: 100,
    min_score: 0.65,
    enable_reranker: false,
    rerank_top_k: 200,
    return_top_k: 20,
  });
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [testQuery, setTestQuery] = useState('');
  const [testResults, setTestResults] = useState<any>(null);
  const [activeTab, setActiveTab] = useState('overview');

  useEffect(() => {
    loadModels();
    loadConfig();
    loadStats();
  }, []);

  const handleLogout = () => {
    document.cookie = 'tuning_auth=; path=/tuning; max-age=0';
    window.location.href = '/';
  };

  const loadModels = async () => {
    try {
      const res = await fetch('/api/tuning/models');
      const data = await res.json();
      setModels(data);
    } catch (error) {
      console.error('Failed to load models:', error);
    }
  };

  const loadConfig = async () => {
    try {
      const res = await fetch('/api/tuning/search/config');
      const data = await res.json();
      setSearchConfig(data);
    } catch (error) {
      console.error('Failed to load config:', error);
    }
  };

  const loadStats = async () => {
    try {
      const res = await fetch('/api/stats');
      const data = await res.json();
      setStats(data);
    } catch (error) {
      console.error('Failed to load stats:', error);
    }
  };

  const switchQueryModel = async (modelKey: string) => {
    try {
      setLoading(true);
      const res = await fetch(`/api/tuning/models/query?model_key=${modelKey}`, {
        method: 'POST',
      });
      const data = await res.json();
      setMessage(data.message);
      await loadModels();
      setTimeout(() => setMessage(''), 3000);
    } catch (error) {
      setMessage('Failed to switch model');
    } finally {
      setLoading(false);
    }
  };

  const updateSearchConfig = async () => {
    try {
      setLoading(true);
      const res = await fetch('/api/tuning/search/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(searchConfig),
      });
      const data = await res.json();
      setMessage(data.message);
      setTimeout(() => setMessage(''), 3000);
    } catch (error) {
      setMessage('Failed to update config');
    } finally {
      setLoading(false);
    }
  };

  const testSearch = async () => {
    if (!testQuery.trim()) return;
    
    try {
      setLoading(true);
      const res = await fetch('/api/tuning/search/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: testQuery, top_k: searchConfig.top_k }),
      });
      const data = await res.json();
      setTestResults(data);
    } catch (error) {
      setMessage('Search test failed');
    } finally {
      setLoading(false);
    }
  };

  const activeQueryModel = models.find(m => m.is_active_query);

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'linear-gradient(to bottom right, #f8fafc, #f1f5f9)', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif' }}>
      {/* Sidebar */}
      <aside style={{ width: '256px', background: 'white', borderRight: '1px solid #e2e8f0', display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '1.5rem', borderBottom: '1px solid #e2e8f0' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div style={{ padding: '0.5rem', background: 'linear-gradient(to bottom right, #3b82f6, #a855f7)', borderRadius: '0.5rem' }}>
              <Settings style={{ width: '1.5rem', height: '1.5rem', color: 'white' }} />
            </div>
            <div>
              <h1 style={{ fontSize: '1.125rem', fontWeight: 700, color: '#1f2937' }}>AI Tuning</h1>
              <p style={{ fontSize: '0.75rem', color: '#6b7280' }}>Dashboard</p>
            </div>
          </div>
        </div>

        <nav style={{ flex: 1, padding: '1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {[
            { id: 'overview', label: 'Overview', icon: BarChart3 },
            { id: 'models', label: 'Models', icon: Zap },
            { id: 'search', label: 'Search Config', icon: Search },
            { id: 'instructions', label: 'Instructions', icon: Settings }
          ].map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setActiveTab(id)}
              style={{
                width: '100%',
                display: 'flex',
                alignItems: 'center',
                gap: '0.75rem',
                padding: '0.75rem 1rem',
                borderRadius: '0.5rem',
                border: 'none',
                background: activeTab === id ? '#eff6ff' : 'transparent',
                color: activeTab === id ? '#2563eb' : '#4b5563',
                cursor: 'pointer',
                transition: 'all 0.2s',
                fontSize: '0.95rem',
                fontWeight: activeTab === id ? 600 : 500
              }}
              onMouseEnter={(e) => {
                if (activeTab !== id) e.currentTarget.style.background = '#f3f4f6';
              }}
              onMouseLeave={(e) => {
                if (activeTab !== id) e.currentTarget.style.background = 'transparent';
              }}
            >
              <Icon style={{ width: '1.25rem', height: '1.25rem' }} />
              <span>{label}</span>
            </button>
          ))}
        </nav>

        <div style={{ padding: '1rem', borderTop: '1px solid #e2e8f0', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          <button
            onClick={() => window.location.href = '/'}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              gap: '0.75rem',
              padding: '0.75rem 1rem',
              borderRadius: '0.5rem',
              border: 'none',
              background: 'transparent',
              color: '#4b5563',
              cursor: 'pointer',
              transition: 'all 0.2s',
              fontSize: '0.95rem',
              fontWeight: 500
            }}
            onMouseEnter={(e) => e.currentTarget.style.background = '#f3f4f6'}
            onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
          >
            <Home style={{ width: '1.25rem', height: '1.25rem' }} />
            <span>Back to App</span>
          </button>
          <button
            onClick={handleLogout}
            style={{
              width: '100%',
              display: 'flex',
              alignItems: 'center',
              gap: '0.75rem',
              padding: '0.75rem 1rem',
              borderRadius: '0.5rem',
              border: 'none',
              background: 'transparent',
              color: '#dc2626',
              cursor: 'pointer',
              transition: 'all 0.2s',
              fontSize: '0.95rem',
              fontWeight: 500
            }}
            onMouseEnter={(e) => e.currentTarget.style.background = '#fee2e2'}
            onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
          >
            <LogOut style={{ width: '1.25rem', height: '1.25rem' }} />
            <span>Logout</span>
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        {/* Header */}
        <header className="bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 px-8 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold text-slate-900 dark:text-white">
                {activeTab === 'overview' && 'Dashboard Overview'}
                {activeTab === 'models' && 'Embedding Models'}
                {activeTab === 'search' && 'Search Configuration'}
                {activeTab === 'instructions' && 'Custom Instructions'}
              </h2>
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                {activeTab === 'overview' && 'Monitor system stats and performance'}
                {activeTab === 'models' && 'Manage and switch embedding models'}
                {activeTab === 'search' && 'Fine-tune search behavior and quality'}
                {activeTab === 'instructions' && 'Configure AI behavior and responses'}
              </p>
            </div>
            {message && (
              <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 text-green-700 dark:text-green-300 px-6 py-3 rounded-xl text-sm font-medium">
                {message}
              </div>
            )}
          </div>
        </header>

        {/* Content Area */}
        <div className="p-8">
          {/* Overview Tab */}
          {activeTab === 'overview' && stats && (
            <div className="space-y-8">
              {/* Stats Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-2xl p-6 text-white shadow-lg">
                  <div className="flex items-center justify-between mb-4">
                    <Database className="w-8 h-8 opacity-80" />
                    <span className="text-sm font-medium opacity-80">Total</span>
                  </div>
                  <div className="text-4xl font-bold mb-1">{stats.total_videos.toLocaleString()}</div>
                  <div className="text-sm opacity-80">Videos Indexed</div>
                </div>

                <div className="bg-gradient-to-br from-green-500 to-green-600 rounded-2xl p-6 text-white shadow-lg">
                  <div className="flex items-center justify-between mb-4">
                    <TrendingUp className="w-8 h-8 opacity-80" />
                    <span className="text-sm font-medium opacity-80">Segments</span>
                  </div>
                  <div className="text-4xl font-bold mb-1">{stats.total_segments.toLocaleString()}</div>
                  <div className="text-sm opacity-80">Total Segments</div>
                </div>

                <div className="bg-gradient-to-br from-amber-500 to-amber-600 rounded-2xl p-6 text-white shadow-lg">
                  <div className="flex items-center justify-between mb-4">
                    <Zap className="w-8 h-8 opacity-80" />
                    <span className="text-sm font-medium opacity-80">Coverage</span>
                  </div>
                  <div className="text-4xl font-bold mb-1">{stats.embedding_coverage}</div>
                  <div className="text-sm opacity-80">Embedding Coverage</div>
                </div>

                <div className="bg-gradient-to-br from-purple-500 to-purple-600 rounded-2xl p-6 text-white shadow-lg">
                  <div className="flex items-center justify-between mb-4">
                    <Settings className="w-8 h-8 opacity-80" />
                    <span className="text-sm font-medium opacity-80">Dimensions</span>
                  </div>
                  <div className="text-4xl font-bold mb-1">{stats.embedding_dimensions}</div>
                  <div className="text-sm opacity-80">Vector Size</div>
                </div>
              </div>

              {/* Active Model Card */}
              <div className="bg-white dark:bg-slate-900 rounded-2xl p-8 border border-slate-200 dark:border-slate-800 shadow-sm">
                <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-4">Active Configuration</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <p className="text-sm text-slate-500 dark:text-slate-400 mb-2">Current Model</p>
                    <p className="text-2xl font-bold text-blue-600 dark:text-blue-400">{activeQueryModel?.key || 'None'}</p>
                  </div>
                  <div>
                    <p className="text-sm text-slate-500 dark:text-slate-400 mb-2">Search Results</p>
                    <p className="text-2xl font-bold text-green-600 dark:text-green-400">Top {searchConfig.top_k}</p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Models Tab */}
          {activeTab === 'models' && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {models.map((model) => (
                <div
                  key={model.key}
                  className={`rounded-2xl p-6 border-2 transition-all shadow-sm ${
                    model.is_active_query
                      ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                      : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-slate-300 dark:hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-start justify-between mb-4">
                    <div>
                      <h3 className="text-xl font-bold text-slate-900 dark:text-white">{model.key}</h3>
                      <p className="text-sm text-slate-500 dark:text-slate-400">{model.provider}</p>
                    </div>
                    {model.is_active_query && (
                      <span className="bg-blue-600 text-white text-xs px-3 py-1 rounded-full font-medium">Active</span>
                    )}
                  </div>
                  
                  <p className="text-slate-700 dark:text-slate-300 mb-6">{model.description}</p>
                  
                  <div className="flex items-center gap-6 mb-6 pb-6 border-t border-slate-200 dark:border-slate-700 pt-6">
                    <div className="flex items-center gap-2">
                      <Database className="w-5 h-5 text-slate-400" />
                      <span className="font-semibold text-slate-900 dark:text-white">{model.dimensions}d</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <DollarSign className="w-5 h-5 text-slate-400" />
                      <span className="font-semibold text-slate-900 dark:text-white">${model.cost_per_1k}/1k</span>
                    </div>
                  </div>
                  
                  {!model.is_active_query && (
                    <button
                      onClick={() => switchQueryModel(model.key)}
                      disabled={loading}
                      className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-slate-400 text-white px-6 py-3 rounded-xl transition-colors font-medium"
                    >
                      Switch to this model
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Search Config Tab */}
          {activeTab === 'search' && (
            <div className="space-y-6">
              <div className="bg-white dark:bg-slate-900 rounded-2xl p-8 border border-slate-200 dark:border-slate-800 shadow-sm">
                <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-6">Search Parameters</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-3">
                      Results to Return (top_k)
                    </label>
                    <input
                      type="number"
                      value={searchConfig.top_k}
                      onChange={(e) => setSearchConfig({ ...searchConfig, top_k: parseInt(e.target.value) })}
                      className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-3">
                      Minimum Score (0.0-1.0)
                    </label>
                    <input
                      type="number"
                      step="0.01"
                      value={searchConfig.min_score}
                      onChange={(e) => setSearchConfig({ ...searchConfig, min_score: parseFloat(e.target.value) })}
                      className="w-full px-4 py-3 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>
                </div>
                <button
                  onClick={updateSearchConfig}
                  disabled={loading}
                  className="mt-8 bg-green-600 hover:bg-green-700 disabled:bg-slate-400 text-white px-8 py-3 rounded-xl transition-colors font-medium"
                >
                  Update Configuration
                </button>
              </div>

              {/* Test Search */}
              <div className="bg-white dark:bg-slate-900 rounded-2xl p-8 border border-slate-200 dark:border-slate-800 shadow-sm">
                <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-6">Test Search</h3>
                <div className="flex gap-4 mb-6">
                  <input
                    type="text"
                    value={testQuery}
                    onChange={(e) => setTestQuery(e.target.value)}
                    placeholder="Enter test query..."
                    className="flex-1 px-4 py-3 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-slate-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    onKeyDown={(e) => e.key === 'Enter' && testSearch()}
                  />
                  <button
                    onClick={testSearch}
                    disabled={loading}
                    className="bg-blue-600 hover:bg-blue-700 disabled:bg-slate-400 text-white px-8 py-3 rounded-xl transition-colors font-medium"
                  >
                    Search
                  </button>
                </div>
                {testResults && (
                  <div className="bg-slate-50 dark:bg-slate-800 rounded-xl p-6 max-h-96 overflow-y-auto">
                    <pre className="text-sm text-slate-700 dark:text-slate-300 whitespace-pre-wrap">
                      {JSON.stringify(testResults, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Instructions Tab */}
          {activeTab === 'instructions' && (
            <div className="bg-white dark:bg-slate-900 rounded-2xl p-8 border border-slate-200 dark:border-slate-800 shadow-sm">
              <CustomInstructionsEditor />
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
