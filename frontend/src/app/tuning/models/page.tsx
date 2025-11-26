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
        setMessage(`Model "${modelKey}" is now active. Changes take effect immediately for new queries.`);
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
      <div className="p-6 flex items-center justify-center min-h-[300px]">
        <p className="text-gray-500">Loading models...</p>
      </div>
    );
  }

  const activeModel = models.find(m => m.is_active_query);

  return (
    <div className="p-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-1">
          Embedding Models
        </h1>
        <p className="text-gray-500 dark:text-gray-400">
          Manage and configure embedding models for semantic search
        </p>
      </div>

      {/* Message */}
      {message && (
        <div className={`flex items-center gap-2 p-4 rounded-lg mb-6 ${
          messageType === 'success' 
            ? 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400' 
            : 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400'
        }`}>
          {messageType === 'success' ? <CheckCircle className="w-5 h-5" /> : <AlertCircle className="w-5 h-5" />}
          {message}
        </div>
      )}

      {/* Active Model Info */}
      {activeModel && (
        <div className="bg-black dark:bg-neutral-800 rounded-xl p-5 text-white mb-8">
          <div className="flex items-center gap-2 mb-3 opacity-80">
            <Zap className="w-5 h-5" />
            <span className="text-sm font-medium">Active Model</span>
          </div>
          <div className="text-2xl font-bold mb-2">{activeModel.key}</div>
          <p className="text-sm opacity-80 mb-4">{activeModel.description}</p>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <p className="text-xs opacity-60 mb-1">Provider</p>
              <p className="font-semibold">{activeModel.provider}</p>
            </div>
            <div>
              <p className="text-xs opacity-60 mb-1">Dimensions</p>
              <p className="font-semibold">{activeModel.dimensions}</p>
            </div>
            <div>
              <p className="text-xs opacity-60 mb-1">Cost</p>
              <p className="font-semibold">{activeModel.cost_per_1k === 0 ? 'Free' : `$${activeModel.cost_per_1k}/1K`}</p>
            </div>
          </div>
        </div>
      )}

      {/* Models Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {models.map((model) => (
          <div
            key={model.key}
            className={`bg-white dark:bg-neutral-900 border rounded-xl p-5 flex flex-col ${
              model.is_active_query 
                ? 'border-black dark:border-white border-2' 
                : 'border-gray-200 dark:border-neutral-800'
            }`}
          >
            {/* Card header */}
            <div className="flex items-start justify-between mb-3">
              <div>
                <h3 className="font-semibold text-gray-900 dark:text-white">{model.key}</h3>
                <p className="text-sm text-gray-500 dark:text-gray-400">{model.provider}</p>
              </div>
              {model.is_active_query && (
                <span className="bg-black dark:bg-white text-white dark:text-black px-2.5 py-0.5 rounded-full text-xs font-semibold">
                  Active
                </span>
              )}
            </div>

            {/* Description */}
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4 line-clamp-2">
              {model.description}
            </p>

            {/* Stats */}
            <div className="grid grid-cols-2 gap-4 py-4 border-y border-gray-100 dark:border-neutral-800 mt-auto">
              <div>
                <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">Dimensions</p>
                <p className="text-xl font-bold text-gray-900 dark:text-white">{model.dimensions}</p>
              </div>
              <div>
                <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">Cost</p>
                <p className={`text-xl font-bold ${model.cost_per_1k === 0 ? 'text-green-600' : 'text-gray-900 dark:text-white'}`}>
                  {model.cost_per_1k === 0 ? 'Free' : `$${model.cost_per_1k}`}
                </p>
              </div>
            </div>
            
            <p className={`text-xs mt-2 ${model.cost_per_1k === 0 ? 'text-green-600' : 'text-gray-400'}`}>
              {model.cost_per_1k === 0 ? '✓ Runs locally, no API costs' : 'Per 1,000 words processed'}
            </p>

            {/* Button */}
            <div className="mt-4">
              {model.is_active_query ? (
                <div className="w-full py-2.5 px-4 bg-gray-100 dark:bg-neutral-800 text-gray-500 dark:text-gray-400 text-center font-medium rounded-lg">
                  Currently active
                </div>
              ) : (
                <button
                  onClick={() => handleSetActive(model.key)}
                  disabled={settingActive !== null}
                  className="w-full py-2.5 px-4 bg-black dark:bg-white text-white dark:text-black font-medium rounded-lg hover:opacity-90 transition-opacity disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  {settingActive === model.key ? (
                    <>
                      <Loader2 className="w-4 h-4 tuning-spinner" />
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
