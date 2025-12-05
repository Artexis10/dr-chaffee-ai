'use client';

import { useState, useEffect, useMemo, useCallback } from 'react';
import { Sparkles, AlertCircle, CheckCircle, Loader2, Info, Check, X, RefreshCw, Cpu } from 'lucide-react';
import '../tuning-pages.css';
import { useSummarizerModels, type SummarizerModel } from '@/hooks/useTuningData';
import { apiFetch } from '@/utils/api';

export default function ModelsPage() {
  const { data: modelsData, loading, error: loadError, isUnauthorized, refresh: refreshModels } = useSummarizerModels();
  const [currentModel, setCurrentModel] = useState<string>('');
  const [settingActive, setSettingActive] = useState<string | null>(null);
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState<'success' | 'error' | 'info'>('info');
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Inline refresh with loading state and confirmation
  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true);
    setMessage('');
    try {
      await refreshModels();
      setMessage('Configuration refreshed from server.');
      setMessageType('success');
      setTimeout(() => setMessage(''), 3000);
    } catch (err) {
      setMessage('Couldn\'t refresh. Please try again.');
      setMessageType('error');
    } finally {
      setIsRefreshing(false);
    }
  }, [refreshModels]);

  // Convert models object to array with keys
  const models = useMemo<SummarizerModel[]>(() => {
    if (!modelsData?.models) return [];
    return Object.entries(modelsData.models).map(([key, model]) => ({
      key,
      ...model
    }));
  }, [modelsData]);

  // Set current model from API data (prefer active_model_name, fallback to current_model)
  useEffect(() => {
    if (modelsData) {
      const activeModelKey = modelsData.active_model_name || modelsData.current_model || '';
      console.log('[ModelsPage] Setting currentModel from API:', activeModelKey, 'modelsData:', modelsData);
      setCurrentModel(activeModelKey);
    }
  }, [modelsData]);

  // Show error from hook
  useEffect(() => {
    if (loadError) {
      setMessage('Failed to load summarizer models. Please try again.');
      setMessageType('error');
    }
  }, [loadError]);

  const handleSetActive = async (modelKey: string) => {
    if (modelKey === currentModel) return;
    
    try {
      setSettingActive(modelKey);
      setMessage('');
      
      const res = await apiFetch('/api/tuning/summarizer/config', {
        method: 'POST',
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

  if (isUnauthorized) {
    return (
      <div className="tuning-page tuning-centered">
        <AlertCircle style={{ width: 48, height: 48, opacity: 0.5, marginBottom: '1rem' }} />
        <p className="tuning-text-muted">Authentication required. Please log in again.</p>
      </div>
    );
  }

  const activeModel = models.find(m => m.key === currentModel);

  return (
    <div className="tuning-page">
      {/* Header */}
      <div className="tuning-header">
        <div>
          <h1 className="tuning-title">Summarizer Model</h1>
          <p className="tuning-text-muted">Choose the AI model used for generating answers</p>
        </div>
        <button 
          onClick={handleRefresh} 
          className="tuning-btn tuning-btn-secondary"
          title="Refresh from server"
          disabled={loading || isRefreshing}
          style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
        >
          <RefreshCw style={{ width: 16, height: 16, animation: isRefreshing ? 'spin 1s linear infinite' : 'none' }} />
        </button>
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
          <p style={{ fontSize: '0.8rem', opacity: 0.75, margin: '0.5rem 0 0 0' }}>
            💡 <strong>Costs shown are per 1,000 tokens</strong> (roughly 750 words). A typical answer uses 500–2,000 tokens.
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

      {/* Active Model Info - Always visible at top */}
      <div className="tuning-stat-card" style={{ marginBottom: '2rem' }}>
        <div className="tuning-stat-header">
          <Cpu style={{ width: 20, height: 20 }} />
          <span>Active Summarizer Model</span>
        </div>
        {loading ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', opacity: 0.7 }}>
            <Loader2 style={{ width: 16, height: 16 }} className="tuning-spinner" />
            <span>Loading summarizer config...</span>
          </div>
        ) : activeModel ? (
          <>
            <div style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '0.5rem' }}>
              {activeModel.name}
              <span style={{ fontSize: '0.875rem', fontWeight: 400, opacity: 0.7, marginLeft: '0.75rem' }}>
                ({currentModel})
              </span>
            </div>
            <p style={{ fontSize: '0.875rem', opacity: 0.8, marginBottom: '1rem' }}>{activeModel.description}</p>
            <div className="tuning-active-model-stats" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(100px, 1fr))', gap: '1rem' }}>
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
          </>
        ) : (
          <div style={{ opacity: 0.7 }}>No model configured</div>
        )}
      </div>

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
                <p className="tuning-model-stat-hint">per 1k tokens</p>
              </div>
              <div>
                <p className="tuning-model-stat-label">Output Cost</p>
                <p className="tuning-model-stat-value" style={{ fontSize: '1rem' }}>{model.cost_output}</p>
                <p className="tuning-model-stat-hint">per 1k tokens</p>
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
