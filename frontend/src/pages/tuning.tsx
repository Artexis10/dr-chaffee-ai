'use client';

import { useState, useEffect } from 'react';
import Head from 'next/head';
import Link from 'next/link';

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
    <>
      <Head>
        <title>AI Tuning Dashboard | Ask Dr. Chaffee</title>
        <meta name="description" content="AI tuning dashboard for embedding models and search configuration" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
      </Head>

      <main className="tuning-container">
        {/* Header */}
        <div className="tuning-header">
          <Link href="/" className="back-link">
            ← Back to Search
          </Link>
          <h1>⚙️ AI Tuning Dashboard</h1>
          <p>Configure embedding models and search parameters</p>
          {message && (
            <div className="message-banner">
              {message}
            </div>
          )}
        </div>

        {/* Stats Cards */}
        {stats && (
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-icon">📊</div>
              <div>
                <p className="stat-label">Total Videos</p>
                <p className="stat-value">{stats.total_videos.toLocaleString()}</p>
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-icon">📝</div>
              <div>
                <p className="stat-label">Total Segments</p>
                <p className="stat-value">{stats.total_segments.toLocaleString()}</p>
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-icon">✨</div>
              <div>
                <p className="stat-label">Embedding Coverage</p>
                <p className="stat-value">{stats.embedding_coverage}</p>
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-icon">🔢</div>
              <div>
                <p className="stat-label">Dimensions</p>
                <p className="stat-value">{stats.embedding_dimensions}</p>
              </div>
            </div>
          </div>
        )}

        {/* Embedding Models */}
        <div className="section">
          <h2>⚡ Embedding Models</h2>
          <p className="section-desc">
            Switch models instantly if embeddings exist. Current: <strong>{activeQueryModel?.key}</strong>
          </p>
          
          <div className="models-grid">
            {models.map((model) => (
              <div
                key={model.key}
                className={`model-card ${model.is_active_query ? 'active' : ''}`}
              >
                <div className="model-header">
                  <h3>{model.key}</h3>
                  {model.is_active_query && <span className="active-badge">Active</span>}
                </div>
                
                <p className="model-provider">{model.provider}</p>
                <p className="model-description">{model.description}</p>
                
                <div className="model-meta">
                  <span>💾 {model.dimensions}d</span>
                  <span>💰 ${model.cost_per_1k}/1k</span>
                </div>
                
                {!model.is_active_query && (
                  <button
                    onClick={() => switchQueryModel(model.key)}
                    disabled={loading}
                    className="switch-btn"
                  >
                    Switch to this model
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Search Configuration */}
        <div className="section">
          <h2>🔍 Search Configuration</h2>
          
          <div className="config-grid">
            <div className="config-field">
              <label>Results to Return (top_k)</label>
              <input
                type="number"
                value={searchConfig.top_k}
                onChange={(e) => setSearchConfig({ ...searchConfig, top_k: parseInt(e.target.value) })}
                min="1"
                max="100"
              />
              <small>Number of results to return (1-100)</small>
            </div>
            
            <div className="config-field">
              <label>Similarity Threshold</label>
              <input
                type="number"
                value={searchConfig.similarity_threshold}
                onChange={(e) => setSearchConfig({ ...searchConfig, similarity_threshold: parseFloat(e.target.value) })}
                min="0"
                max="1"
                step="0.1"
              />
              <small>Minimum similarity score (0.0-1.0)</small>
            </div>
            
            <div className="config-field checkbox">
              <label>
                <input
                  type="checkbox"
                  checked={searchConfig.enable_reranker}
                  onChange={(e) => setSearchConfig({ ...searchConfig, enable_reranker: e.target.checked })}
                />
                Enable Reranker
              </label>
              <small>Use cross-encoder for better quality (slower)</small>
            </div>
            
            {searchConfig.enable_reranker && (
              <div className="config-field">
                <label>Rerank Candidates</label>
                <input
                  type="number"
                  value={searchConfig.rerank_top_k}
                  onChange={(e) => setSearchConfig({ ...searchConfig, rerank_top_k: parseInt(e.target.value) })}
                  min="1"
                  max="500"
                />
                <small>Candidates to rerank (1-500)</small>
              </div>
            )}
          </div>
          
          <button
            onClick={updateSearchConfig}
            disabled={loading}
            className="primary-btn"
          >
            Update Search Config
          </button>
        </div>

        {/* Test Search */}
        <div className="section">
          <h2>🧪 Test Search</h2>
          
          <div className="search-input-group">
            <input
              type="text"
              value={testQuery}
              onChange={(e) => setTestQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && testSearch()}
              placeholder="Enter a test query..."
              className="search-input"
            />
            <button
              onClick={testSearch}
              disabled={loading || !testQuery.trim()}
              className="primary-btn"
            >
              Search
            </button>
          </div>
          
          {testResults.length > 0 && (
            <div className="results-list">
              {testResults.map((result, idx) => (
                <div key={idx} className="result-item">
                  <div className="result-meta">
                    <span className="similarity">
                      {(result.similarity * 100).toFixed(1)}% match
                    </span>
                    <span className="timestamp">
                      {result.youtube_id} @ {Math.floor(result.start_sec / 60)}:{String(Math.floor(result.start_sec % 60)).padStart(2, '0')}
                    </span>
                  </div>
                  <p className="result-text">{result.text}</p>
                  {result.speaker_label && (
                    <span className="speaker-badge">{result.speaker_label}</span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        <style jsx>{`
          .tuning-container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
            min-height: 100vh;
            color: #e2e8f0;
          }

          .tuning-header {
            margin-bottom: 3rem;
          }

          .back-link {
            display: inline-block;
            margin-bottom: 1rem;
            color: #64748b;
            text-decoration: none;
            font-size: 0.9rem;
            transition: color 0.2s;
          }

          .back-link:hover {
            color: #94a3b8;
          }

          .tuning-header h1 {
            font-size: 2.5rem;
            margin-bottom: 0.5rem;
            color: #f1f5f9;
          }

          .tuning-header p {
            color: #94a3b8;
            font-size: 1.1rem;
          }

          .message-banner {
            margin-top: 1rem;
            padding: 1rem;
            background: rgba(34, 197, 94, 0.1);
            border: 1px solid #22c55e;
            color: #86efac;
            border-radius: 8px;
            font-size: 0.9rem;
          }

          .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 3rem;
          }

          .stat-card {
            display: flex;
            align-items: center;
            gap: 1rem;
            padding: 1.5rem;
            background: rgba(30, 41, 59, 0.5);
            border: 1px solid #334155;
            border-radius: 12px;
            backdrop-filter: blur(10px);
          }

          .stat-icon {
            font-size: 2rem;
          }

          .stat-label {
            font-size: 0.85rem;
            color: #94a3b8;
            margin: 0;
          }

          .stat-value {
            font-size: 1.8rem;
            font-weight: bold;
            color: #f1f5f9;
            margin: 0.25rem 0 0 0;
          }

          .section {
            margin-bottom: 3rem;
            padding: 2rem;
            background: rgba(30, 41, 59, 0.3);
            border: 1px solid #334155;
            border-radius: 12px;
            backdrop-filter: blur(10px);
          }

          .section h2 {
            font-size: 1.5rem;
            margin-bottom: 0.5rem;
            color: #f1f5f9;
          }

          .section-desc {
            color: #94a3b8;
            margin-bottom: 1.5rem;
            font-size: 0.95rem;
          }

          .models-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 1rem;
            margin-bottom: 1rem;
          }

          .model-card {
            padding: 1.5rem;
            background: rgba(15, 23, 42, 0.5);
            border: 1px solid #475569;
            border-radius: 8px;
            transition: all 0.2s;
          }

          .model-card.active {
            border-color: #3b82f6;
            background: rgba(59, 130, 246, 0.1);
          }

          .model-card:hover {
            border-color: #64748b;
          }

          .model-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.5rem;
          }

          .model-header h3 {
            margin: 0;
            font-size: 1.1rem;
            color: #f1f5f9;
          }

          .active-badge {
            background: #3b82f6;
            color: white;
            padding: 0.25rem 0.75rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: bold;
          }

          .model-provider {
            color: #94a3b8;
            font-size: 0.85rem;
            margin: 0 0 0.5rem 0;
          }

          .model-description {
            color: #cbd5e1;
            font-size: 0.9rem;
            margin-bottom: 1rem;
          }

          .model-meta {
            display: flex;
            gap: 1rem;
            font-size: 0.85rem;
            color: #94a3b8;
            margin-bottom: 1rem;
          }

          .switch-btn {
            width: 100%;
            padding: 0.75rem;
            background: #3b82f6;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 500;
            transition: background 0.2s;
          }

          .switch-btn:hover {
            background: #2563eb;
          }

          .switch-btn:disabled {
            background: #64748b;
            cursor: not-allowed;
          }

          .config-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1.5rem;
            margin-bottom: 1.5rem;
          }

          .config-field {
            display: flex;
            flex-direction: column;
          }

          .config-field.checkbox {
            justify-content: center;
          }

          .config-field label {
            font-weight: 500;
            margin-bottom: 0.5rem;
            color: #f1f5f9;
            font-size: 0.95rem;
          }

          .config-field.checkbox label {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            cursor: pointer;
          }

          .config-field input[type="number"],
          .config-field input[type="text"] {
            padding: 0.75rem;
            background: rgba(15, 23, 42, 0.5);
            border: 1px solid #475569;
            border-radius: 6px;
            color: #f1f5f9;
            font-size: 0.95rem;
          }

          .config-field input[type="number"]:focus,
          .config-field input[type="text"]:focus {
            outline: none;
            border-color: #3b82f6;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
          }

          .config-field small {
            color: #94a3b8;
            font-size: 0.8rem;
            margin-top: 0.25rem;
          }

          .primary-btn {
            padding: 0.75rem 1.5rem;
            background: #22c55e;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 500;
            transition: background 0.2s;
          }

          .primary-btn:hover {
            background: #16a34a;
          }

          .primary-btn:disabled {
            background: #64748b;
            cursor: not-allowed;
          }

          .search-input-group {
            display: flex;
            gap: 1rem;
            margin-bottom: 1.5rem;
          }

          .search-input {
            flex: 1;
            padding: 0.75rem;
            background: rgba(15, 23, 42, 0.5);
            border: 1px solid #475569;
            border-radius: 6px;
            color: #f1f5f9;
            font-size: 0.95rem;
          }

          .search-input:focus {
            outline: none;
            border-color: #3b82f6;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
          }

          .results-list {
            display: flex;
            flex-direction: column;
            gap: 1rem;
          }

          .result-item {
            padding: 1rem;
            background: rgba(15, 23, 42, 0.5);
            border: 1px solid #475569;
            border-radius: 8px;
          }

          .result-meta {
            display: flex;
            justify-content: space-between;
            margin-bottom: 0.75rem;
            font-size: 0.85rem;
          }

          .similarity {
            color: #22c55e;
            font-weight: 500;
          }

          .timestamp {
            color: #94a3b8;
          }

          .result-text {
            color: #cbd5e1;
            margin: 0;
            line-height: 1.5;
          }

          .speaker-badge {
            display: inline-block;
            margin-top: 0.75rem;
            padding: 0.25rem 0.75rem;
            background: rgba(59, 130, 246, 0.2);
            color: #93c5fd;
            border-radius: 4px;
            font-size: 0.8rem;
          }

          @media (max-width: 768px) {
            .tuning-container {
              padding: 1rem;
            }

            .tuning-header h1 {
              font-size: 1.8rem;
            }

            .models-grid {
              grid-template-columns: 1fr;
            }

            .config-grid {
              grid-template-columns: 1fr;
            }

            .search-input-group {
              flex-direction: column;
            }
          }
        `}</style>
      </main>
    </>
  );
}
