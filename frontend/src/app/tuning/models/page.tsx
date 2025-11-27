'use client';

import { useState, useEffect } from 'react';
import { Zap, AlertCircle, CheckCircle, Loader2, Info } from 'lucide-react';
import '../tuning-pages.css';

interface EmbeddingModel {
  key: string;
  provider: string;
  dimensions: number;
  cost_per_1k: number;
  description: string;
  is_active_query: boolean;
}

export default function ModelsPage() {
  const [models, setModels] = useState<EmbeddingModel[]>([]);
  const [loading, setLoading] = useState(true);
  const [settingActive, setSettingActive] = useState<string | null>(null);
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState<'success' | 'error' | 'info'>('info');

  useEffect(() => {
    loadModels();
  }, []);

  const loadModels = async () => {
    try {
      const res = await fetch('/api/embedding-models');
      if (!res.ok) {
        throw new Error(`Failed to load models: ${res.status}`);
      }
      const data = await res.json();
      if (Array.isArray(data)) {
        setModels(data);
      } else {
        throw new Error('Invalid response format');
      }
    } catch (error) {
      console.error('Failed to load models:', error);
      setMessage('Failed to load embedding models. Please try again.');
      setMessageType('error');
    } finally {
      setLoading(false);
    }
  };

  // Model switching is disabled - show tooltip message instead
  const handleSetActive = (modelKey: string) => {
    // Do not make API call - switching is disabled
    setMessage('Model switching is temporarily disabled. A re-embedding service is required to safely switch embedding models.');
    setMessageType('info');
  };

  if (loading) {
    return (
      <div className="tuning-page tuning-centered">
        <p className="tuning-text-muted">Loading models...</p>
      </div>
    );
  }

  const activeModel = models.find(m => m.is_active_query);

  return (
    <div className="tuning-page">
      {/* Header */}
      <div className="tuning-header">
        <h1 className="tuning-title">Embedding Models</h1>
        <p className="tuning-text-muted">View configured embedding models for semantic search</p>
      </div>

      {/* Model Switching Disabled Banner */}
      <div className="tuning-alert tuning-alert-info">
        <Info style={{ width: 20, height: 20, flexShrink: 0, marginTop: 2 }} />
        <div>
          <p style={{ fontWeight: 600, marginBottom: 4 }}>Model Switching Disabled</p>
          <p style={{ fontSize: '0.875rem', opacity: 0.9, margin: 0 }}>
            Embedding model switching is currently disabled. A full re-embedding process is required 
            to safely change models, as different models produce incompatible embeddings. 
            Contact your developer if you need to change models.
          </p>
        </div>
      </div>

      {/* Message */}
      {message && (
        <div className={`tuning-alert ${messageType === 'success' ? 'tuning-alert-success' : 'tuning-alert-error'}`}>
          {messageType === 'success' ? <CheckCircle style={{ width: 20, height: 20 }} /> : <AlertCircle style={{ width: 20, height: 20 }} />}
          {message}
        </div>
      )}

      {/* Active Model Info */}
      {activeModel && (
        <div className="tuning-stat-card" style={{ marginBottom: '2rem' }}>
          <div className="tuning-stat-header">
            <Zap style={{ width: 20, height: 20 }} />
            <span>Active Model</span>
          </div>
          <div style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '0.5rem' }}>{activeModel.key}</div>
          <p style={{ fontSize: '0.875rem', opacity: 0.8, marginBottom: '1rem' }}>{activeModel.description}</p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem' }}>
            <div>
              <p style={{ fontSize: '0.75rem', opacity: 0.6, marginBottom: '0.25rem' }}>Provider</p>
              <p style={{ fontWeight: 600 }}>{activeModel.provider}</p>
            </div>
            <div>
              <p style={{ fontSize: '0.75rem', opacity: 0.6, marginBottom: '0.25rem' }}>Dimensions</p>
              <p style={{ fontWeight: 600 }}>{activeModel.dimensions}</p>
            </div>
            <div>
              <p style={{ fontSize: '0.75rem', opacity: 0.6, marginBottom: '0.25rem' }}>Cost</p>
              <p style={{ fontWeight: 600 }}>{activeModel.cost_per_1k === 0 ? 'Free' : `$${activeModel.cost_per_1k}/1K`}</p>
            </div>
          </div>
        </div>
      )}

      {/* Models Grid */}
      <div className="tuning-model-grid">
        {models.map((model) => (
          <div key={model.key} className={`tuning-model-card ${model.is_active_query ? 'active' : ''}`}>
            {/* Card header */}
            <div className="tuning-model-header">
              <div>
                <h3 className="tuning-model-name">{model.key}</h3>
                <p className="tuning-model-provider">{model.provider}</p>
              </div>
              {model.is_active_query && <span className="tuning-badge">Active</span>}
            </div>

            {/* Description */}
            <p className="tuning-text-muted" style={{ fontSize: '0.875rem', marginBottom: '1rem', minHeight: '2.5rem' }}>
              {model.description}
            </p>

            {/* Stats */}
            <div className="tuning-model-stats">
              <div>
                <p className="tuning-model-stat-label">Dimensions</p>
                <p className="tuning-model-stat-value">{model.dimensions}</p>
              </div>
              <div>
                <p className="tuning-model-stat-label">Cost</p>
                <p className={`tuning-model-stat-value ${model.cost_per_1k === 0 ? 'free' : ''}`}>
                  {model.cost_per_1k === 0 ? 'Free' : `$${model.cost_per_1k}`}
                </p>
              </div>
            </div>
            
            <p style={{ fontSize: '0.75rem', marginTop: '0.5rem', color: model.cost_per_1k === 0 ? '#059669' : 'var(--text-muted)' }}>
              {model.cost_per_1k === 0 ? '✓ Runs locally, no API costs' : 'Per 1,000 words processed'}
            </p>

            {/* Button */}
            <div style={{ marginTop: '1rem' }}>
              {model.is_active_query ? (
                <div className="tuning-btn tuning-btn-secondary" style={{ opacity: 0.7, cursor: 'default' }}>
                  Currently active
                </div>
              ) : (
                <button
                  disabled={true}
                  className="tuning-btn tuning-btn-primary tuning-btn-disabled"
                  title="Model switching is temporarily disabled. A re-embedding service is required to safely switch embedding models."
                  style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}
                >
                  Set as Active
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
