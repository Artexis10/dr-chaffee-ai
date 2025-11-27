'use client';

import { useState, useEffect } from 'react';
import { Sparkles, AlertCircle, CheckCircle, Loader2, Info, Check, X } from 'lucide-react';
import '../tuning-pages.css';

interface SummarizerModel {
  key: string;
  name: string;
  provider: string;
  quality_tier: string;
  cost_input: string;
  cost_output: string;
  speed: string;
  recommended: boolean;
  pros: string[];
  cons: string[];
  description: string;
}

interface SummarizerModelsResponse {
  current_model: string;
  models: Record<string, Omit<SummarizerModel, 'key'>>;
}

export default function ModelsPage() {
  const [models, setModels] = useState<SummarizerModel[]>([]);
  const [currentModel, setCurrentModel] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [settingActive, setSettingActive] = useState<string | null>(null);
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState<'success' | 'error' | 'info'>('info');

  useEffect(() => {
    loadModels();
  }, []);

  const loadModels = async () => {
    try {
      const res = await fetch('/api/tuning/summarizer/models');
      if (!res.ok) {
        throw new Error(`Failed to load models: ${res.status}`);
      }
      const data: SummarizerModelsResponse = await res.json();
      
      // Convert models object to array with keys
      const modelArray: SummarizerModel[] = Object.entries(data.models).map(([key, model]) => ({
        key,
        ...model
      }));
      
      setModels(modelArray);
      setCurrentModel(data.current_model);
    } catch (error) {
      console.error('Failed to load models:', error);
      setMessage('Failed to load summarizer models. Please try again.');
      setMessageType('error');
    } finally {
      setLoading(false);
    }
  };

  const handleSetActive = async (modelKey: string) => {
    if (modelKey === currentModel) return;
    
    try {
      setSettingActive(modelKey);
      setMessage('');
      
      const res = await fetch('/api/tuning/summarizer/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          model: modelKey,
          temperature: 0.1,
          max_tokens: 2000
        })
      });
      
      const data = await res.json();
      
      if (res.ok && data.success) {
        setCurrentModel(modelKey);
        setMessage(`Summarizer model changed to "${modelKey}". Changes take effect immediately.`);
        setMessageType('success');
      } else {
        const errorMsg = data.error || data.detail || 'Failed to update model';
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

  const getQualityBadgeClass = (tier: string) => {
    switch (tier.toLowerCase()) {
      case 'best': return 'tuning-quality-best';
      case 'high': return 'tuning-quality-high';
      case 'budget': return 'tuning-quality-budget';
      default: return '';
    }
  };

  if (loading) {
    return (
      <div className="tuning-page tuning-centered">
        <p className="tuning-text-muted">Loading models...</p>
      </div>
    );
  }

  const activeModel = models.find(m => m.key === currentModel);

  return (
    <div className="tuning-page">
      {/* Header */}
      <div className="tuning-header">
        <h1 className="tuning-title">Summarizer Model</h1>
        <p className="tuning-text-muted">Choose the AI model used for generating answers</p>
      </div>

      {/* Info Banner */}
      <div className="tuning-alert tuning-alert-info">
        <Info style={{ width: 20, height: 20, flexShrink: 0, marginTop: 2 }} />
        <div>
          <p style={{ fontWeight: 600, marginBottom: 4 }}>Answer Generation Only</p>
          <p style={{ fontSize: '0.875rem', opacity: 0.9, margin: 0 }}>
            This setting controls which OpenAI model generates answers from search results. 
            It does <strong>not</strong> affect search quality or embeddings — those use a separate local model.
          </p>
        </div>
      </div>

      {/* Message */}
      {message && (
        <div className={`tuning-alert ${messageType === 'success' ? 'tuning-alert-success' : messageType === 'error' ? 'tuning-alert-error' : 'tuning-alert-info'}`}>
          {messageType === 'success' ? <CheckCircle style={{ width: 20, height: 20 }} /> : <AlertCircle style={{ width: 20, height: 20 }} />}
          {message}
        </div>
      )}

      {/* Active Model Info */}
      {activeModel && (
        <div className="tuning-stat-card" style={{ marginBottom: '2rem' }}>
          <div className="tuning-stat-header">
            <Sparkles style={{ width: 20, height: 20 }} />
            <span>Active Summarizer</span>
          </div>
          <div style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '0.5rem' }}>{activeModel.name}</div>
          <p style={{ fontSize: '0.875rem', opacity: 0.8, marginBottom: '1rem' }}>{activeModel.description}</p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem' }}>
            <div>
              <p style={{ fontSize: '0.75rem', opacity: 0.6, marginBottom: '0.25rem' }}>Provider</p>
              <p style={{ fontWeight: 600 }}>{activeModel.provider}</p>
            </div>
            <div>
              <p style={{ fontSize: '0.75rem', opacity: 0.6, marginBottom: '0.25rem' }}>Quality</p>
              <p style={{ fontWeight: 600 }}>{activeModel.quality_tier}</p>
            </div>
            <div>
              <p style={{ fontSize: '0.75rem', opacity: 0.6, marginBottom: '0.25rem' }}>Speed</p>
              <p style={{ fontWeight: 600, textTransform: 'capitalize' }}>{activeModel.speed}</p>
            </div>
          </div>
        </div>
      )}

      {/* Models Grid */}
      <div className="tuning-model-grid">
        {models.map((model) => (
          <div key={model.key} className={`tuning-model-card ${model.key === currentModel ? 'active' : ''}`}>
            {/* Card header */}
            <div className="tuning-model-header">
              <div>
                <h3 className="tuning-model-name">{model.name}</h3>
                <p className="tuning-model-provider">{model.provider}</p>
              </div>
              <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                <span className={`tuning-quality-badge ${getQualityBadgeClass(model.quality_tier)}`}>
                  {model.quality_tier}
                </span>
                {model.key === currentModel && <span className="tuning-badge">Active</span>}
              </div>
            </div>

            {/* Description */}
            <p className="tuning-text-muted" style={{ fontSize: '0.875rem', marginBottom: '1rem' }}>
              {model.description}
            </p>

            {/* Pros/Cons */}
            <div style={{ marginBottom: '1rem' }}>
              {model.pros.map((pro, idx) => (
                <div key={`pro-${idx}`} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.8rem', marginBottom: '0.25rem' }}>
                  <Check style={{ width: 14, height: 14, color: '#059669', flexShrink: 0 }} />
                  <span style={{ color: 'var(--text-muted)' }}>{pro}</span>
                </div>
              ))}
              {model.cons.map((con, idx) => (
                <div key={`con-${idx}`} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.8rem', marginBottom: '0.25rem' }}>
                  <X style={{ width: 14, height: 14, color: '#dc2626', flexShrink: 0 }} />
                  <span style={{ color: 'var(--text-muted)' }}>{con}</span>
                </div>
              ))}
            </div>

            {/* Cost Stats */}
            <div className="tuning-model-stats">
              <div>
                <p className="tuning-model-stat-label">Input Cost</p>
                <p className="tuning-model-stat-value" style={{ fontSize: '1rem' }}>{model.cost_input}</p>
              </div>
              <div>
                <p className="tuning-model-stat-label">Output Cost</p>
                <p className="tuning-model-stat-value" style={{ fontSize: '1rem' }}>{model.cost_output}</p>
              </div>
            </div>

            {/* Button */}
            <div style={{ marginTop: '1rem' }}>
              {model.key === currentModel ? (
                <div className="tuning-btn tuning-btn-secondary" style={{ opacity: 0.7, cursor: 'default' }}>
                  Currently active
                </div>
              ) : (
                <button
                  onClick={() => handleSetActive(model.key)}
                  disabled={settingActive !== null}
                  className="tuning-btn tuning-btn-primary"
                  style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}
                >
                  {settingActive === model.key ? (
                    <>
                      <Loader2 style={{ width: 16, height: 16 }} className="tuning-spinner" />
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
