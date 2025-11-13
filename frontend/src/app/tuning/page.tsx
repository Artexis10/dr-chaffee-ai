'use client';

import { useState, useEffect } from 'react';
import { Settings, Zap, DollarSign, Database, TrendingUp, Search } from 'lucide-react';
import CustomInstructionsEditor from '@/components/CustomInstructionsEditor';

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

  useEffect(() => {
    loadModels();
    loadConfig();
    loadStats();
  }, []);

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
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 text-white p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold flex items-center gap-3">
              <Settings className="w-10 h-10 text-blue-400" />
              AI Tuning Dashboard
            </h1>
            <p className="text-slate-400 mt-2">Configure embedding models and search parameters</p>
          </div>
          {message && (
            <div className="bg-green-500/20 border border-green-500 text-green-300 px-4 py-2 rounded-lg">
              {message}
            </div>
          )}
        </div>

        {/* Stats Cards */}
        {stats && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-slate-400 text-sm">Total Videos</p>
                  <p className="text-3xl font-bold mt-1">{stats.total_videos.toLocaleString()}</p>
                </div>
                <Database className="w-8 h-8 text-blue-400" />
              </div>
            </div>
            <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-slate-400 text-sm">Total Segments</p>
                  <p className="text-3xl font-bold mt-1">{stats.total_segments.toLocaleString()}</p>
                </div>
                <TrendingUp className="w-8 h-8 text-green-400" />
              </div>
            </div>
            <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-slate-400 text-sm">Embedding Coverage</p>
                  <p className="text-3xl font-bold mt-1">{stats.embedding_coverage}</p>
                </div>
                <Zap className="w-8 h-8 text-yellow-400" />
              </div>
            </div>
            <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-slate-400 text-sm">Dimensions</p>
                  <p className="text-3xl font-bold mt-1">{stats.embedding_dimensions}</p>
                </div>
                <Settings className="w-8 h-8 text-purple-400" />
              </div>
            </div>
          </div>
        )}

        {/* Custom Instructions Editor */}
        <CustomInstructionsEditor />

        {/* Embedding Models */}
        <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-6">
          <h2 className="text-2xl font-bold mb-4 flex items-center gap-2">
            <Zap className="w-6 h-6 text-yellow-400" />
            Embedding Models
          </h2>
          <p className="text-slate-400 mb-6">
            Switch models instantly if embeddings exist. Current: <span className="text-blue-400 font-semibold">{activeQueryModel?.key}</span>
          </p>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {models.map((model) => (
              <div
                key={model.key}
                className={`border rounded-lg p-4 transition-all ${
                  model.is_active_query
                    ? 'border-blue-500 bg-blue-500/10'
                    : 'border-slate-600 bg-slate-800/30 hover:border-slate-500'
                }`}
              >
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <h3 className="font-semibold text-lg">{model.key}</h3>
                    <p className="text-sm text-slate-400">{model.provider}</p>
                  </div>
                  {model.is_active_query && (
                    <span className="bg-blue-500 text-white text-xs px-2 py-1 rounded">Active</span>
                  )}
                </div>
                
                <p className="text-sm text-slate-300 mb-3">{model.description}</p>
                
                <div className="flex items-center gap-4 text-sm mb-3">
                  <div className="flex items-center gap-1">
                    <Database className="w-4 h-4 text-purple-400" />
                    <span>{model.dimensions}d</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <DollarSign className="w-4 h-4 text-green-400" />
                    <span>${model.cost_per_1k}/1k</span>
                  </div>
                </div>
                
                {!model.is_active_query && (
                  <button
                    onClick={() => switchQueryModel(model.key)}
                    disabled={loading}
                    className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-slate-600 text-white px-4 py-2 rounded-lg transition-colors"
                  >
                    Switch to this model
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Search Configuration */}
        <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-6">
          <h2 className="text-2xl font-bold mb-4 flex items-center gap-2">
            <Search className="w-6 h-6 text-green-400" />
            Search Configuration
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
            <div>
              <label className="block text-sm font-medium mb-2">
                Results to Return (top_k)
              </label>
              <input
                type="number"
                value={searchConfig.top_k}
                onChange={(e) => setSearchConfig({ ...searchConfig, top_k: parseInt(e.target.value) })}
                className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2 focus:border-blue-500 focus:outline-none"
                min="1"
                max="100"
              />
              <p className="text-xs text-slate-400 mt-1">Number of results to return (1-100)</p>
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-2">
                Similarity Threshold
              </label>
              <input
                type="number"
                value={searchConfig.similarity_threshold}
                onChange={(e) => setSearchConfig({ ...searchConfig, similarity_threshold: parseFloat(e.target.value) })}
                className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2 focus:border-blue-500 focus:outline-none"
                min="0"
                max="1"
                step="0.1"
              />
              <p className="text-xs text-slate-400 mt-1">Minimum similarity score (0.0-1.0)</p>
            </div>
            
            <div>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={searchConfig.enable_reranker}
                  onChange={(e) => setSearchConfig({ ...searchConfig, enable_reranker: e.target.checked })}
                  className="w-4 h-4"
                />
                <span className="text-sm font-medium">Enable Reranker</span>
              </label>
              <p className="text-xs text-slate-400 mt-1">Use cross-encoder for better quality (slower)</p>
            </div>
            
            {searchConfig.enable_reranker && (
              <div>
                <label className="block text-sm font-medium mb-2">
                  Rerank Candidates
                </label>
                <input
                  type="number"
                  value={searchConfig.rerank_top_k}
                  onChange={(e) => setSearchConfig({ ...searchConfig, rerank_top_k: parseInt(e.target.value) })}
                  className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2 focus:border-blue-500 focus:outline-none"
                  min="1"
                  max="500"
                />
                <p className="text-xs text-slate-400 mt-1">Candidates to rerank (1-500)</p>
              </div>
            )}
          </div>
          
          <button
            onClick={updateSearchConfig}
            disabled={loading}
            className="bg-green-600 hover:bg-green-700 disabled:bg-slate-600 text-white px-6 py-2 rounded-lg transition-colors"
          >
            Update Search Config
          </button>
        </div>

        {/* Test Search */}
        <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-6">
          <h2 className="text-2xl font-bold mb-4">Test Search</h2>
          
          <div className="flex gap-4 mb-6">
            <input
              type="text"
              value={testQuery}
              onChange={(e) => setTestQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && testSearch()}
              placeholder="Enter a test query..."
              className="flex-1 bg-slate-700 border border-slate-600 rounded-lg px-4 py-2 focus:border-blue-500 focus:outline-none"
            />
            <button
              onClick={testSearch}
              disabled={loading || !testQuery.trim()}
              className="bg-blue-600 hover:bg-blue-700 disabled:bg-slate-600 text-white px-6 py-2 rounded-lg transition-colors"
            >
              Search
            </button>
          </div>
          
          {testResults.length > 0 && (
            <div className="space-y-3">
              {testResults.map((result, idx) => (
                <div key={idx} className="bg-slate-700/50 border border-slate-600 rounded-lg p-4">
                  <div className="flex items-start justify-between mb-2">
                    <span className="text-xs text-slate-400">
                      Similarity: {(result.similarity * 100).toFixed(1)}%
                    </span>
                    <span className="text-xs text-slate-400">
                      {result.youtube_id} @ {Math.floor(result.start_sec / 60)}:{String(Math.floor(result.start_sec % 60)).padStart(2, '0')}
                    </span>
                  </div>
                  <p className="text-sm">{result.text}</p>
                  {result.speaker_label && (
                    <span className="inline-block mt-2 text-xs bg-blue-500/20 text-blue-300 px-2 py-1 rounded">
                      {result.speaker_label}
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
