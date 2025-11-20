'use client';

import { useState, useEffect } from 'react';
import { Zap, DollarSign } from 'lucide-react';

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
  const [message, setMessage] = useState('');

  useEffect(() => {
    loadModels();
  }, []);

  const loadModels = async () => {
    try {
      const res = await fetch('/api/embedding-models');
      const data = await res.json();
      setModels(data);
    } catch (error) {
      console.error('Failed to load models:', error);
      setMessage('Failed to load embedding models');
    } finally {
      setLoading(false);
    }
  };

  const handleSetActive = async (modelKey: string) => {
    try {
      setMessage('');
      const res = await fetch('/api/embedding-models/set-active', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model_key: modelKey })
      });
      
      if (res.ok) {
        setMessage('Active model updated successfully');
        loadModels();
      } else {
        setMessage('Failed to update active model');
      }
    } catch (error) {
      console.error('Error setting active model:', error);
      setMessage('Error updating active model');
    }
  };

  if (loading) {
    return (
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <p style={{ color: '#6b7280' }}>Loading models...</p>
      </div>
    );
  }

  const activeModel = models.find(m => m.is_active_query);

  return (
    <div style={{ padding: '2rem' }}>
      {/* Header */}
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '2rem', fontWeight: 700, color: '#1f2937', marginBottom: '0.5rem' }}>
          Embedding Models
        </h1>
        <p style={{ color: '#6b7280' }}>
          Manage and configure embedding models for semantic search
        </p>
      </div>

      {/* Message */}
      {message && (
        <div style={{
          background: message.includes('success') ? '#d1fae5' : '#fee2e2',
          color: message.includes('success') ? '#065f46' : '#991b1b',
          padding: '1rem',
          borderRadius: '0.5rem',
          marginBottom: '1.5rem',
          border: `1px solid ${message.includes('success') ? '#a7f3d0' : '#fecaca'}`
        }}>
          {message}
        </div>
      )}

      {/* Active Model Info */}
      {activeModel && (
        <div style={{
          background: '#000000',
          borderRadius: '1rem',
          padding: '1.5rem',
          color: 'white',
          marginBottom: '2rem',
          boxShadow: '0 4px 12px rgba(0, 0, 0, 0.2)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
            <Zap style={{ width: '1.5rem', height: '1.5rem' }} />
            <span style={{ fontSize: '0.875rem', fontWeight: 500, opacity: 0.9 }}>Active Model</span>
          </div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '0.5rem' }}>
            {activeModel.key}
          </h2>
          <p style={{ opacity: 0.9, marginBottom: '1rem' }}>
            {activeModel.description}
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '1rem' }}>
            <div>
              <p style={{ fontSize: '0.75rem', opacity: 0.8, marginBottom: '0.25rem' }}>Provider</p>
              <p style={{ fontSize: '1.125rem', fontWeight: 600 }}>{activeModel.provider}</p>
            </div>
            <div>
              <p style={{ fontSize: '0.75rem', opacity: 0.8, marginBottom: '0.25rem' }}>Dimensions</p>
              <p style={{ fontSize: '1.125rem', fontWeight: 600 }}>{activeModel.dimensions}</p>
            </div>
            <div>
              <p style={{ fontSize: '0.75rem', opacity: 0.8, marginBottom: '0.25rem' }}>Cost per 1K</p>
              <p style={{ fontSize: '1.125rem', fontWeight: 600 }}>${activeModel.cost_per_1k}</p>
            </div>
          </div>
        </div>
      )}

      {/* Models Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '1.5rem' }}>
        {models.map((model) => (
          <div
            key={model.key}
            style={{
              background: 'white',
              border: model.is_active_query ? '2px solid #000000' : '1px solid #e5e7eb',
              borderRadius: '0.75rem',
              padding: '1.5rem',
              transition: 'all 0.2s'
            }}
            onMouseEnter={(e) => {
              if (!model.is_active_query) {
                e.currentTarget.style.borderColor = '#d1d5db';
                e.currentTarget.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.1)';
              }
            }}
            onMouseLeave={(e) => {
              if (!model.is_active_query) {
                e.currentTarget.style.borderColor = '#e5e7eb';
                e.currentTarget.style.boxShadow = 'none';
              }
            }}
          >
            <div style={{ display: 'flex', alignItems: 'start', justifyContent: 'space-between', marginBottom: '1rem' }}>
              <div>
                <h3 style={{ fontSize: '1.125rem', fontWeight: 700, color: '#1f2937', marginBottom: '0.25rem' }}>
                  {model.key}
                </h3>
                <p style={{ fontSize: '0.875rem', color: '#6b7280' }}>
                  {model.provider}
                </p>
              </div>
              {model.is_active_query && (
                <div style={{
                  background: '#f5f5f5',
                  color: '#000000',
                  padding: '0.25rem 0.75rem',
                  borderRadius: '9999px',
                  fontSize: '0.75rem',
                  fontWeight: 600
                }}>
                  Active
                </div>
              )}
            </div>

            <p style={{ color: '#4b5563', marginBottom: '1rem', fontSize: '0.875rem' }}>
              {model.description}
            </p>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem', paddingBottom: '1rem', borderBottom: '1px solid #e5e7eb' }}>
              <div>
                <p style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '0.25rem' }}>Dimensions</p>
                <p style={{ fontSize: '1.25rem', fontWeight: 600, color: '#1f2937' }}>
                  {model.dimensions}
                </p>
              </div>
              <div>
                <p style={{ fontSize: '0.75rem', color: '#6b7280', marginBottom: '0.25rem' }}>Cost per 1K</p>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                  <DollarSign style={{ width: '1rem', height: '1rem', color: '#10b981' }} />
                  <p style={{ fontSize: '1.25rem', fontWeight: 600, color: '#1f2937' }}>
                    {model.cost_per_1k}
                  </p>
                </div>
              </div>
            </div>

            {!model.is_active_query && (
              <button
                onClick={() => handleSetActive(model.key)}
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  background: '#000000',
                  color: 'white',
                  border: 'none',
                  borderRadius: '0.5rem',
                  fontWeight: 500,
                  cursor: 'pointer',
                  transition: 'background 0.2s'
                }}
                onMouseEnter={(e) => e.currentTarget.style.background = '#333333'}
                onMouseLeave={(e) => e.currentTarget.style.background = '#000000'}
              >
                Set as Active
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
