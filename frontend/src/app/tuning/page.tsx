'use client';

import { useState, useEffect } from 'react';
import { Settings, Zap, DollarSign, Database, TrendingUp, Search, LogOut } from 'lucide-react';
import CustomInstructionsEditor from '@/components/CustomInstructionsEditor';
import { useRouter } from 'next/navigation';

interface EmbeddingModel {
  key: string;
  provider: string;
  model_name: string;
  dimensions: number;
  cost_per_1k: number;
  description: string;
  is_active_query: boolean;
  is_active_ingestion: boolean;
}

interface SearchConfig {
  top_k: number;
  similarity_threshold: number;
  enable_reranker: boolean;
  rerank_top_k: number;
}

interface Stats {
  total_segments: number;
  total_videos: number;
  segments_with_embeddings: number;
  unique_speakers: number;
  embedding_dimensions: number;
  embedding_coverage: string;
}

interface SearchResult {
  text: string;
  similarity: number;
  source_id: number;
  youtube_id: string;
  start_sec: number;
  end_sec: number;
  speaker_label: string | null;
}

export default function TuningPage() {
  const router = useRouter();
  
  const [models, setModels] = useState<EmbeddingModel[]>([]);
  const [searchConfig, setSearchConfig] = useState<SearchConfig>({
    top_k: 20,
    similarity_threshold: 0.0,
    enable_reranker: false,
    rerank_top_k: 200,
  });
  const [stats, setStats] = useState<Stats | null>(null);
  const [testQuery, setTestQuery] = useState('');
  const [testResults, setTestResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');

  // Load data on mount
  useEffect(() => {
    loadModels();
    loadConfig();
    loadStats();
  }, []);

  const handleLogout = () => {
    // Clear auth cookie
    document.cookie = 'tuning_auth=; path=/tuning; max-age=0';
    router.push('/tuning/auth');
    router.refresh();
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
      const res = await fetch('/api/tuning/config');
      const data = await res.json();
      setSearchConfig(data.search_config);
    } catch (error) {
      console.error('Failed to load config:', error);
    }
  };

  const loadStats = async () => {
    try {
      const res = await fetch('/api/tuning/stats');
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
    <div className="min-h-screen bg-white dark:bg-slate-950 text-slate-900 dark:text-white">
      {/* Header */}
      <header className="sticky top-0 z-50 border-b border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950">
        <div className="px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
              <Settings className="w-6 h-6 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold">AI Tuning Dashboard</h1>
              <p className="text-sm text-slate-600 dark:text-slate-400">Manage AI behavior and search parameters</p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            {message && (
              <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 text-green-700 dark:text-green-300 px-4 py-2 rounded-lg text-sm">
                {message}
              </div>
            )}
            <button
              onClick={handleLogout}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors text-slate-700 dark:text-slate-300"
            >
              <LogOut className="w-4 h-4" />
              Logout
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="mx-auto px-6 py-12 space-y-8 max-w-6xl">

        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-gradient-to-br from-blue-50 to-blue-100 dark:from-blue-900/20 dark:to-blue-900/10 border border-blue-200 dark:border-blue-800 rounded-xl p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-blue-600 dark:text-blue-400 text-sm font-medium">Total Videos</p>
                  <p className="text-3xl font-bold text-blue-900 dark:text-blue-100 mt-2">{stats.total_videos.toLocaleString()}</p>
                </div>
                <Database className="w-8 h-8 text-blue-400 dark:text-blue-300 opacity-50" />
              </div>
            </div>
            <div className="bg-gradient-to-br from-green-50 to-green-100 dark:from-green-900/20 dark:to-green-900/10 border border-green-200 dark:border-green-800 rounded-xl p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-green-600 dark:text-green-400 text-sm font-medium">Total Segments</p>
                  <p className="text-3xl font-bold text-green-900 dark:text-green-100 mt-2">{stats.total_segments.toLocaleString()}</p>
                </div>
                <TrendingUp className="w-8 h-8 text-green-400 dark:text-green-300 opacity-50" />
              </div>
            </div>
            <div className="bg-gradient-to-br from-amber-50 to-amber-100 dark:from-amber-900/20 dark:to-amber-900/10 border border-amber-200 dark:border-amber-800 rounded-xl p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-amber-600 dark:text-amber-400 text-sm font-medium">Embedding Coverage</p>
                  <p className="text-3xl font-bold text-amber-900 dark:text-amber-100 mt-2">{stats.embedding_coverage}</p>
                </div>
                <Zap className="w-8 h-8 text-amber-400 dark:text-amber-300 opacity-50" />
              </div>
            </div>
            <div className="bg-gradient-to-br from-purple-50 to-purple-100 dark:from-purple-900/20 dark:to-purple-900/10 border border-purple-200 dark:border-purple-800 rounded-xl p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-purple-600 dark:text-purple-400 text-sm font-medium">Dimensions</p>
                  <p className="text-3xl font-bold text-purple-900 dark:text-purple-100 mt-2">{stats.embedding_dimensions}</p>
                </div>
                <Settings className="w-8 h-8 text-purple-400 dark:text-purple-300 opacity-50" />
              </div>
            </div>
          </div>
        )}

        {/* Custom Instructions Editor */}
        <CustomInstructionsEditor />

        {/* Embedding Models */}
        <section className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-8">
          <h2 className="text-2xl font-bold mb-2 flex items-center gap-3 text-slate-900 dark:text-white">
            <div className="p-2 bg-amber-100 dark:bg-amber-900/30 rounded-lg">
              <Zap className="w-5 h-5 text-amber-600 dark:text-amber-400" />
            </div>
            Embedding Models
          </h2>
          <p className="text-slate-600 dark:text-slate-400 mb-6">
            Switch models instantly if embeddings exist. Current: <span className="text-blue-600 dark:text-blue-400 font-semibold">{activeQueryModel?.key}</span>
          </p>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {models.map((model) => (
              <div
                key={model.key}
                className={`border rounded-lg p-5 transition-all ${
                  model.is_active_query
                    ? 'border-blue-300 dark:border-blue-600 bg-blue-50 dark:bg-blue-900/20'
                    : 'border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 hover:border-slate-300 dark:hover:border-slate-600'
                }`}
              >
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <h3 className="font-semibold text-lg text-slate-900 dark:text-white">{model.key}</h3>
                    <p className="text-sm text-slate-600 dark:text-slate-400">{model.provider}</p>
                  </div>
                  {model.is_active_query && (
                    <span className="bg-blue-600 dark:bg-blue-500 text-white text-xs px-2 py-1 rounded-full font-medium">Active</span>
                  )}
                </div>
                
                <p className="text-sm text-slate-700 dark:text-slate-300 mb-4">{model.description}</p>
                
                <div className="flex items-center gap-4 text-sm mb-4 pb-4 border-t border-slate-200 dark:border-slate-700 pt-4">
                  <div className="flex items-center gap-2 text-slate-600 dark:text-slate-400">
                    <Database className="w-4 h-4" />
                    <span className="font-medium">{model.dimensions}d</span>
                  </div>
                  <div className="flex items-center gap-2 text-slate-600 dark:text-slate-400">
                    <DollarSign className="w-4 h-4" />
                    <span className="font-medium">${model.cost_per_1k}/1k</span>
                  </div>
                </div>
                
                {!model.is_active_query && (
                  <button
                    onClick={() => switchQueryModel(model.key)}
                    disabled={loading}
                    className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-slate-400 dark:disabled:bg-slate-600 text-white px-4 py-2 rounded-lg transition-colors font-medium"
                  >
                    Switch to this model
                  </button>
                )}
              </div>
            ))}
          </div>
        </section>

        {/* Search Configuration */}
        <section className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-8">
          <h2 className="text-2xl font-bold mb-2 flex items-center gap-3 text-slate-900 dark:text-white">
            <div className="p-2 bg-green-100 dark:bg-green-900/30 rounded-lg">
              <Search className="w-5 h-5 text-green-600 dark:text-green-400" />
            </div>
            Search Configuration
          </h2>
          <p className="text-slate-600 dark:text-slate-400 mb-6">Fine-tune search behavior and result quality</p>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div>
              <label className="block text-sm font-medium text-slate-900 dark:text-white mb-2">
                Results to Return (top_k)
              </label>
              <input
                type="number"
                value={searchConfig.top_k}
                onChange={(e) => setSearchConfig({ ...searchConfig, top_k: parseInt(e.target.value) })}
                className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-4 py-2 text-slate-900 dark:text-white focus:border-blue-500 dark:focus:border-blue-400 focus:outline-none focus:ring-1 focus:ring-blue-500"
                min="1"
                max="100"
              />
              <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">Number of results to return (1-100)</p>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-slate-900 dark:text-white mb-2">
                Similarity Threshold
              </label>
              <input
                type="number"
                value={searchConfig.similarity_threshold}
                onChange={(e) => setSearchConfig({ ...searchConfig, similarity_threshold: parseFloat(e.target.value) })}
                className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-4 py-2 text-slate-900 dark:text-white focus:border-blue-500 dark:focus:border-blue-400 focus:outline-none focus:ring-1 focus:ring-blue-500"
                min="0"
                max="1"
                step="0.1"
              />
              <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">Minimum similarity score (0.0-1.0)</p>
            </div>
            
            <div className="flex items-center gap-3">
              <input
                type="checkbox"
                id="enable_reranker"
                checked={searchConfig.enable_reranker}
                onChange={(e) => setSearchConfig({ ...searchConfig, enable_reranker: e.target.checked })}
                className="w-4 h-4 rounded border-slate-300 dark:border-slate-600 text-blue-600 focus:ring-blue-500"
              />
              <label htmlFor="enable_reranker" className="text-sm font-medium text-slate-900 dark:text-white cursor-pointer">
                Enable Reranker
              </label>
              <p className="text-xs text-slate-600 dark:text-slate-400">Use cross-encoder for better quality (slower)</p>
            </div>
            
            {searchConfig.enable_reranker && (
              <div>
                <label className="block text-sm font-medium text-slate-900 dark:text-white mb-2">
                  Rerank Candidates
                </label>
                <input
                  type="number"
                  value={searchConfig.rerank_top_k}
                  onChange={(e) => setSearchConfig({ ...searchConfig, rerank_top_k: parseInt(e.target.value) })}
                  className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-4 py-2 text-slate-900 dark:text-white focus:border-blue-500 dark:focus:border-blue-400 focus:outline-none focus:ring-1 focus:ring-blue-500"
                  min="1"
                  max="500"
                />
                <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">Candidates to rerank (1-500)</p>
              </div>
            )}
          </div>
          
          <button
            onClick={updateSearchConfig}
            disabled={loading}
            className="bg-green-600 hover:bg-green-700 disabled:bg-slate-400 dark:disabled:bg-slate-600 text-white px-6 py-2 rounded-lg transition-colors font-medium"
          >
            Update Search Config
          </button>
        </section>

        {/* Test Search */}
        <section className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-8">
          <h2 className="text-2xl font-bold mb-2 flex items-center gap-3 text-slate-900 dark:text-white">
            <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
              <Search className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            </div>
            Test Search
          </h2>
          <p className="text-slate-600 dark:text-slate-400 mb-6">Try a test query to see search results</p>
          
          <div className="flex gap-4 mb-6">
            <input
              type="text"
              value={testQuery}
              onChange={(e) => setTestQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && testSearch()}
              placeholder="Enter a test query..."
              className="flex-1 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-4 py-2 text-slate-900 dark:text-white placeholder-slate-500 dark:placeholder-slate-400 focus:border-blue-500 dark:focus:border-blue-400 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
            <button
              onClick={testSearch}
              disabled={loading || !testQuery.trim()}
              className="bg-blue-600 hover:bg-blue-700 disabled:bg-slate-400 dark:disabled:bg-slate-600 text-white px-6 py-2 rounded-lg transition-colors font-medium"
            >
              Search
            </button>
          </div>
          
          {testResults.length > 0 && (
            <div className="space-y-3">
              {testResults.map((result, idx) => (
                <div key={idx} className="bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 rounded-lg p-4">
                  <div className="flex items-start justify-between mb-2">
                    <span className="text-xs text-slate-600 dark:text-slate-400 font-medium">
                      Similarity: {(result.similarity * 100).toFixed(1)}%
                    </span>
                    <span className="text-xs text-slate-600 dark:text-slate-400">
                      {result.youtube_id} @ {Math.floor(result.start_sec / 60)}:{String(Math.floor(result.start_sec % 60)).padStart(2, '0')}
                    </span>
                  </div>
                  <p className="text-sm text-slate-900 dark:text-slate-100">{result.text}</p>
                  {result.speaker_label && (
                    <span className="inline-block mt-2 text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 px-2 py-1 rounded">
                      {result.speaker_label}
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
