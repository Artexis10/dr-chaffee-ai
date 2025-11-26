'use client';

import { useState, useEffect } from 'react';
import { Zap, AlertCircle, CheckCircle, Loader2 } from 'lucide-react';

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

  const handleSetActive = async (modelKey: string) => {
    try {
      setSettingActive(modelKey);
      setMessage('');
      
      const res = await fetch('/api/embedding-models/set-active', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model_key: modelKey })
      });
      
      const data = await res.json();
      
      if (res.ok) {
        setMessage(`Model "${modelKey}" is now active. Note: A server restart may be required for full effect.`);
        setMessageType('success');
        await loadModels();
      } else {
        const errorMsg = data.error || data.detail || 'Failed to update active model';
        setMessage(errorMsg);
        setMessageType('error');
      }
    } catch (error) {
      console.error('Error setting active model:', error);
      setMessage('Network error. Please check your connection and try again.');
      setMessageType('error');
    } finally {
      setSettingActive(null);
    }
  };

  if (loading) {
    return (
      <div className="tuning-page">
        <div className="tuning-loading">Loading models...</div>
      </div>
    );
  }

  const activeModel = models.find(m => m.is_active_query);

  return (
    <div className="tuning-page">
      {/* Header */}
      <div className="tuning-page-header">
        <h1 className="tuning-page-title">Embedding Models</h1>
        <p className="tuning-page-description">
          Manage and configure embedding models for semantic search
        </p>
      </div>

      {/* Message */}
      {message && (
        <div className={`tuning-message tuning-message-${messageType}`}>
          {messageType === 'success' ? <CheckCircle /> : <AlertCircle />}
          {message}
        </div>
      )}

      {/* Active Model Info */}
      {activeModel && (
        <div className="tuning-stat-card" style={{ marginBottom: '2rem' }}>
          <div className="tuning-stat-header">
            <Zap />
            <span className="tuning-stat-label">Active Model</span>
          </div>
          <div className="tuning-stat-value" style={{ fontSize: '1.5rem' }}>
            {activeModel.key}
          </div>
          <p className="tuning-stat-description" style={{ marginBottom: '1rem' }}>
            {activeModel.description}
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '1rem' }}>
            <div>
              <p style={{ fontSize: '0.75rem', opacity: 0.8, marginBottom: '0.25rem' }}>Provider</p>
              <p style={{ fontSize: '1rem', fontWeight: 600 }}>{activeModel.provider}</p>
            </div>
            <div>
              <p style={{ fontSize: '0.75rem', opacity: 0.8, marginBottom: '0.25rem' }}>Dimensions</p>
              <p style={{ fontSize: '1rem', fontWeight: 600 }}>{activeModel.dimensions}</p>
            </div>
            <div>
              <p style={{ fontSize: '0.75rem', opacity: 0.8, marginBottom: '0.25rem' }}>Cost/1K words</p>
              <p style={{ fontSize: '1rem', fontWeight: 600 }}>{activeModel.cost_per_1k === 0 ? 'Free' : `$${activeModel.cost_per_1k}`}</p>
            </div>
          </div>
        </div>
      )}

      {/* Models Grid */}
      <div className="tuning-models-grid">
        {models.map((model) => (
          <div
            key={model.key}
            className={`tuning-model-card ${model.is_active_query ? 'active' : ''}`}
          >
            {/* Card header */}
            <div style={{ display: 'flex', alignItems: 'start', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
              <div>
                <h3 className="tuning-card-title" style={{ marginBottom: '0.25rem' }}>
                  {model.key}
                </h3>
                <p className="tuning-input-hint">
                  {model.provider}
                </p>
              </div>
              {model.is_active_query && (
                <span style={{
                  background: 'var(--accent, #000000)',
                  color: 'var(--accent-foreground, #ffffff)',
                  padding: '0.25rem 0.75rem',
                  borderRadius: '9999px',
                  fontSize: '0.75rem',
                  fontWeight: 600
                }}>
                  Active
                </span>
              )}
            </div>

            {/* Card body */}
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
              <p className="tuning-input-hint" style={{ 
                marginBottom: '1rem', 
                minHeight: '2.5rem',
                overflow: 'hidden',
                display: '-webkit-box',
                WebkitLineClamp: 2,
                WebkitBoxOrient: 'vertical'
              }}>
                {model.description}
              </p>

              {/* Stats */}
              <div style={{ 
                display: 'grid', 
                gridTemplateColumns: '1fr 1fr', 
                gap: '1rem', 
                padding: '1rem 0',
                borderTop: '1px solid var(--border-subtle, #e5e7eb)',
                borderBottom: '1px solid var(--border-subtle, #e5e7eb)',
                marginTop: 'auto'
              }}>
                <div>
                  <p className="tuning-input-hint" style={{ marginBottom: '0.25rem', textTransform: 'uppercase', fontSize: '0.7rem', letterSpacing: '0.05em' }}>Dimensions</p>
                  <p style={{ fontSize: '1.25rem', fontWeight: 700 }}>
                    {model.dimensions}
                  </p>
                </div>
                <div>
                  <p className="tuning-input-hint" style={{ marginBottom: '0.25rem', textTransform: 'uppercase', fontSize: '0.7rem', letterSpacing: '0.05em' }}>Cost</p>
                  <p style={{ fontSize: '1.25rem', fontWeight: 700, color: model.cost_per_1k === 0 ? '#059669' : 'inherit' }}>
                    {model.cost_per_1k === 0 ? 'Free' : `$${model.cost_per_1k}`}
                  </p>
                </div>
              </div>
              
              <p className="tuning-input-hint" style={{ paddingTop: '0.5rem', fontSize: '0.75rem', color: model.cost_per_1k === 0 ? '#059669' : undefined }}>
                {model.cost_per_1k === 0 ? '✓ Runs locally, no API costs' : 'Per 1,000 words processed'}
              </p>
            </div>

            {/* Card footer */}
            <div style={{ marginTop: '1rem' }}>
              {model.is_active_query ? (
                <div className="tuning-btn tuning-btn-secondary" style={{ cursor: 'default', opacity: 0.7 }}>
                  Currently active
                </div>
              ) : (
                <button
                  onClick={() => handleSetActive(model.key)}
                  disabled={settingActive !== null}
                  className="tuning-btn tuning-btn-primary"
                  style={{ width: '100%' }}
                >
                  {settingActive === model.key ? (
                    <>
                      <Loader2 className="tuning-spinner" style={{ width: '1rem', height: '1rem' }} />
                      Setting...
                    </>
                  ) : (
                    'Set as Active'
                  )}
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
