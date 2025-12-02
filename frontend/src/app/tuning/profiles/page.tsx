'use client';

import { useState, useEffect } from 'react';
import { FileText, Save, Check, X, Plus, Trash2, Edit2, AlertCircle } from 'lucide-react';
import '../tuning-pages.css';

interface RagProfile {
  id?: string;
  name: string;
  description?: string;
  base_instructions: string;
  style_instructions?: string;
  retrieval_hints?: string;
  model_name: string;
  max_context_tokens: number;
  temperature: number;
  version?: number;
  is_default: boolean;
  created_at?: string;
  updated_at?: string;
}

interface RagModel {
  key: string;
  label: string;
  max_tokens: number;
  supports_json_mode: boolean;
  supports_128k_context: boolean;
  recommended: boolean;
}

// Fallback models if API fails
const FALLBACK_MODELS: RagModel[] = [
  { key: 'gpt-4.1', label: 'GPT-4.1 (Best quality)', max_tokens: 128000, supports_json_mode: true, supports_128k_context: true, recommended: true },
  { key: 'gpt-4o-mini', label: 'GPT-4o Mini (Cheapest)', max_tokens: 128000, supports_json_mode: true, supports_128k_context: true, recommended: true },
];

export default function ProfilesPage() {
  const [profiles, setProfiles] = useState<RagProfile[]>([]);
  const [ragModels, setRagModels] = useState<RagModel[]>(FALLBACK_MODELS);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [editMode, setEditMode] = useState(false);
  const [formData, setFormData] = useState<RagProfile>({
    name: '',
    description: '',
    base_instructions: '',
    style_instructions: '',
    retrieval_hints: '',
    model_name: 'gpt-4.1',
    max_context_tokens: 8000,
    temperature: 0.3,
    is_default: false,
  });

  useEffect(() => {
    loadProfiles();
    loadRagModels();
  }, []);

  const loadRagModels = async () => {
    try {
      const res = await fetch('/api/tuning/models/rag', { credentials: 'include' });
      if (!res.ok) {
        console.warn('Failed to load RAG models from API, using fallback');
        return;
      }
      const data = await res.json();
      if (Array.isArray(data) && data.length > 0) {
        setRagModels(data);
      }
    } catch (err) {
      console.warn('Failed to load RAG models:', err);
      // Keep using fallback models
    }
  };

  const loadProfiles = async () => {
    try {
      setLoading(true);
      const res = await fetch('/api/tuning/profiles', { credentials: 'include' });
      if (!res.ok) throw new Error('Failed to load profiles');
      const data = await res.json();
      setProfiles(data);
      setError(null);
    } catch (err) {
      console.error('Failed to load profiles:', err);
      setError(err instanceof Error ? err.message : 'Failed to load profiles');
    } finally {
      setLoading(false);
    }
  };

  const showMessage = (msg: string, isError = false) => {
    if (isError) {
      setError(msg);
      setMessage(null);
    } else {
      setMessage(msg);
      setError(null);
    }
    setTimeout(() => {
      setError(null);
      setMessage(null);
    }, 5000);
  };

  const saveProfile = async () => {
    try {
      setSaving(true);
      const url = formData.id
        ? `/api/tuning/profiles/${formData.id}`
        : '/api/tuning/profiles';
      const method = formData.id ? 'PUT' : 'POST';

      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(formData),
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Failed to save profile');
      }

      showMessage('Profile saved successfully!');
      setEditMode(false);
      loadProfiles();
    } catch (err) {
      showMessage(err instanceof Error ? err.message : 'Failed to save', true);
    } finally {
      setSaving(false);
    }
  };

  const activateProfile = async (id: string) => {
    try {
      setSaving(true);
      const res = await fetch(`/api/tuning/profiles/${id}/activate`, {
        method: 'POST',
        credentials: 'include',
      });
      if (!res.ok) throw new Error('Failed to activate profile');
      showMessage('Profile activated!');
      loadProfiles();
    } catch (err) {
      showMessage(err instanceof Error ? err.message : 'Failed to activate', true);
    } finally {
      setSaving(false);
    }
  };

  const deleteProfile = async (id: string, name: string) => {
    if (!confirm(`Delete profile "${name}"? This cannot be undone.`)) return;
    
    try {
      setSaving(true);
      const res = await fetch(`/api/tuning/profiles/${id}`, {
        method: 'DELETE',
        credentials: 'include',
      });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Failed to delete');
      }
      showMessage('Profile deleted');
      loadProfiles();
    } catch (err) {
      showMessage(err instanceof Error ? err.message : 'Failed to delete', true);
    } finally {
      setSaving(false);
    }
  };

  const startNewProfile = () => {
    setFormData({
      name: '',
      description: '',
      base_instructions: '',
      style_instructions: '',
      retrieval_hints: '',
      model_name: 'gpt-4.1',
      max_context_tokens: 8000,
      temperature: 0.3,
      is_default: false,
    });
    setEditMode(true);
  };

  const editProfile = (profile: RagProfile) => {
    setFormData(profile);
    setEditMode(true);
  };

  if (loading) {
    return (
      <div className="tuning-page tuning-centered">
        <p className="tuning-text-muted">Loading profiles...</p>
      </div>
    );
  }

  return (
    <div className="tuning-page">
      {/* Header */}
      <div className="tuning-header">
        <div>
          <h1 className="tuning-title">RAG Profiles</h1>
          <p className="tuning-text-muted">Configure AI persona, voice, and retrieval behavior</p>
        </div>
        {!editMode && (
          <button onClick={startNewProfile} className="tuning-btn tuning-btn-primary">
            <Plus style={{ width: 16, height: 16 }} />
            New Profile
          </button>
        )}
      </div>

      {/* Messages */}
      {error && (
        <div className="tuning-alert tuning-alert-error">
          <AlertCircle style={{ width: 20, height: 20 }} />
          {error}
        </div>
      )}
      {message && (
        <div className="tuning-alert tuning-alert-success">
          <Check style={{ width: 20, height: 20 }} />
          {message}
        </div>
      )}

      {/* Edit Mode */}
      {editMode ? (
        <div className="tuning-card">
          <h3 className="tuning-card-title">
            {formData.id ? 'Edit Profile' : 'New Profile'}
          </h3>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            {/* Name & Description */}
            <div className="tuning-grid-2">
              <div>
                <label className="tuning-label">Profile Name *</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g., default, technical, casual"
                  className="tuning-input"
                  maxLength={255}
                />
              </div>
              <div>
                <label className="tuning-label">Description</label>
                <input
                  type="text"
                  value={formData.description || ''}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="What this profile does"
                  className="tuning-input"
                />
              </div>
            </div>

            {/* Model Settings */}
            <div className="tuning-grid-3">
              <div>
                <label className="tuning-label">Model</label>
                <select
                  value={formData.model_name}
                  onChange={(e) => setFormData({ ...formData, model_name: e.target.value })}
                  className="tuning-select"
                >
                  {ragModels.map((m) => (
                    <option key={m.key} value={m.key}>
                      {m.label}{m.recommended ? ' ★' : ''}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="tuning-label">Temperature ({formData.temperature})</label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={formData.temperature}
                  onChange={(e) => setFormData({ ...formData, temperature: parseFloat(e.target.value) })}
                  className="tuning-range"
                />
              </div>
              <div>
                <label className="tuning-label">Max Context Tokens</label>
                <input
                  type="number"
                  value={formData.max_context_tokens}
                  onChange={(e) => setFormData({ ...formData, max_context_tokens: parseInt(e.target.value) || 8000 })}
                  min={1000}
                  max={32000}
                  className="tuning-input"
                />
              </div>
            </div>

            {/* Base Instructions */}
            <div>
              <label className="tuning-label">
                Base Instructions (Voice & Approach) *
                <span className="tuning-text-muted" style={{ fontWeight: 400, marginLeft: 8 }}>
                  {formData.base_instructions.length} chars
                </span>
              </label>
              <textarea
                value={formData.base_instructions}
                onChange={(e) => setFormData({ ...formData, base_instructions: e.target.value })}
                placeholder="Define the AI's speaking style, content approach, and persona..."
                className="tuning-textarea"
                rows={10}
              />
            </div>

            {/* Style Instructions */}
            <div>
              <label className="tuning-label">
                Style Instructions (What to Avoid/Aim For)
                <span className="tuning-text-muted" style={{ fontWeight: 400, marginLeft: 8 }}>
                  {(formData.style_instructions || '').length} chars
                </span>
              </label>
              <textarea
                value={formData.style_instructions || ''}
                onChange={(e) => setFormData({ ...formData, style_instructions: e.target.value })}
                placeholder="List things to avoid and things to aim for..."
                className="tuning-textarea"
                rows={8}
              />
            </div>

            {/* Retrieval Hints */}
            <div>
              <label className="tuning-label">
                Retrieval Hints (Citation Rules)
                <span className="tuning-text-muted" style={{ fontWeight: 400, marginLeft: 8 }}>
                  {(formData.retrieval_hints || '').length} chars
                </span>
              </label>
              <textarea
                value={formData.retrieval_hints || ''}
                onChange={(e) => setFormData({ ...formData, retrieval_hints: e.target.value })}
                placeholder="Rules for how to use and cite retrieved context..."
                className="tuning-textarea"
                rows={6}
              />
            </div>

            {/* Set as Default */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <input
                type="checkbox"
                id="is_default"
                checked={formData.is_default}
                onChange={(e) => setFormData({ ...formData, is_default: e.target.checked })}
              />
              <label htmlFor="is_default" style={{ cursor: 'pointer' }}>
                Set as active profile (used for all answers)
              </label>
            </div>

            {/* Buttons */}
            <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
              <button
                onClick={saveProfile}
                disabled={saving || !formData.name || !formData.base_instructions}
                className="tuning-btn tuning-btn-primary"
              >
                <Save style={{ width: 16, height: 16 }} />
                {saving ? 'Saving...' : formData.id ? 'Save Changes' : 'Create Profile'}
              </button>
              <button
                onClick={() => {
                  setEditMode(false);
                  loadProfiles();
                }}
                className="tuning-btn tuning-btn-secondary"
              >
                <X style={{ width: 16, height: 16 }} />
                Cancel
              </button>
            </div>
          </div>
        </div>
      ) : (
        /* List Mode */
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {profiles.map((profile) => (
            <div
              key={profile.id || profile.name}
              className="tuning-card"
              style={{
                borderColor: profile.is_default ? 'var(--accent)' : undefined,
                borderWidth: profile.is_default ? 2 : 1,
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem', flexWrap: 'wrap' }}>
                <div style={{ flex: 1, minWidth: 200 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                    <h3 className="tuning-card-title" style={{ margin: 0 }}>{profile.name}</h3>
                    {profile.is_default && (
                      <span style={{
                        background: 'var(--accent)',
                        color: 'white',
                        fontSize: '0.65rem',
                        padding: '0.2rem 0.5rem',
                        borderRadius: '9999px',
                        fontWeight: 600,
                        textTransform: 'uppercase',
                      }}>Active</span>
                    )}
                    {profile.version && (
                      <span className="tuning-text-muted" style={{ fontSize: '0.75rem' }}>v{profile.version}</span>
                    )}
                  </div>
                  {profile.description && (
                    <p className="tuning-text-muted" style={{ fontSize: '0.875rem', marginBottom: '0.5rem' }}>
                      {profile.description}
                    </p>
                  )}
                  <div className="tuning-text-muted" style={{ fontSize: '0.75rem' }}>
                    Model: {profile.model_name} • Temp: {profile.temperature} • Max tokens: {profile.max_context_tokens}
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '0.5rem', flexShrink: 0 }}>
                  <button
                    onClick={() => editProfile(profile)}
                    className="tuning-btn tuning-btn-secondary"
                    style={{ padding: '0.5rem 0.75rem' }}
                  >
                    <Edit2 style={{ width: 14, height: 14 }} />
                    Edit
                  </button>
                  {!profile.is_default && profile.id && (
                    <>
                      <button
                        onClick={() => activateProfile(profile.id!)}
                        disabled={saving}
                        className="tuning-btn tuning-btn-primary"
                        style={{ padding: '0.5rem 0.75rem' }}
                      >
                        <Check style={{ width: 14, height: 14 }} />
                        Activate
                      </button>
                      <button
                        onClick={() => deleteProfile(profile.id!, profile.name)}
                        disabled={saving}
                        className="tuning-btn tuning-btn-danger"
                        style={{ padding: '0.5rem 0.75rem' }}
                      >
                        <Trash2 style={{ width: 14, height: 14 }} />
                      </button>
                    </>
                  )}
                </div>
              </div>

              {/* Preview of instructions */}
              <div style={{ marginTop: '1rem', paddingTop: '1rem', borderTop: '1px solid var(--border-subtle)' }}>
                <details>
                  <summary style={{ cursor: 'pointer', fontSize: '0.875rem', fontWeight: 500 }}>
                    View Instructions ({profile.base_instructions.length + (profile.style_instructions?.length || 0) + (profile.retrieval_hints?.length || 0)} chars total)
                  </summary>
                  <div style={{ marginTop: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                    {profile.base_instructions && (
                      <div>
                        <div className="tuning-text-muted" style={{ fontSize: '0.75rem', marginBottom: '0.25rem' }}>Base Instructions:</div>
                        <pre style={{
                          background: 'var(--bg-card-elevated)',
                          padding: '0.75rem',
                          borderRadius: '0.375rem',
                          fontSize: '0.75rem',
                          whiteSpace: 'pre-wrap',
                          maxHeight: '150px',
                          overflow: 'auto',
                        }}>
                          {profile.base_instructions}
                        </pre>
                      </div>
                    )}
                    {profile.style_instructions && (
                      <div>
                        <div className="tuning-text-muted" style={{ fontSize: '0.75rem', marginBottom: '0.25rem' }}>Style Instructions:</div>
                        <pre style={{
                          background: 'var(--bg-card-elevated)',
                          padding: '0.75rem',
                          borderRadius: '0.375rem',
                          fontSize: '0.75rem',
                          whiteSpace: 'pre-wrap',
                          maxHeight: '150px',
                          overflow: 'auto',
                        }}>
                          {profile.style_instructions}
                        </pre>
                      </div>
                    )}
                    {profile.retrieval_hints && (
                      <div>
                        <div className="tuning-text-muted" style={{ fontSize: '0.75rem', marginBottom: '0.25rem' }}>Retrieval Hints:</div>
                        <pre style={{
                          background: 'var(--bg-card-elevated)',
                          padding: '0.75rem',
                          borderRadius: '0.375rem',
                          fontSize: '0.75rem',
                          whiteSpace: 'pre-wrap',
                          maxHeight: '150px',
                          overflow: 'auto',
                        }}>
                          {profile.retrieval_hints}
                        </pre>
                      </div>
                    )}
                  </div>
                </details>
              </div>
            </div>
          ))}

          {profiles.length === 0 && (
            <div className="tuning-card tuning-centered">
              <FileText style={{ width: 48, height: 48, opacity: 0.3 }} />
              <p className="tuning-text-muted" style={{ marginTop: '1rem' }}>No profiles found. Create one to get started.</p>
            </div>
          )}
        </div>
      )}

      {/* Info Card */}
      <div className="tuning-card" style={{ marginTop: '1.5rem' }}>
        <h3 className="tuning-card-title">How RAG Profiles Work</h3>
        <div className="tuning-text-muted" style={{ fontSize: '0.875rem', lineHeight: 1.6 }}>
          <p style={{ marginBottom: '0.75rem' }}>
            RAG profiles control how the AI generates answers. The <strong>active profile</strong> is used for all answer generation.
          </p>
          <ul style={{ paddingLeft: '1.25rem', margin: 0 }}>
            <li><strong>Base Instructions</strong>: Define the AI&apos;s voice, speaking style, and content approach</li>
            <li><strong>Style Instructions</strong>: Specify what to avoid and what to aim for</li>
            <li><strong>Retrieval Hints</strong>: Rules for citing and using retrieved context</li>
            <li><strong>Model & Temperature</strong>: Control which OpenAI model to use and its creativity level</li>
          </ul>
          <p style={{ marginTop: '0.75rem', fontSize: '0.8rem', opacity: 0.8 }}>
            Note: Core safety rules (AI identity, no hallucinations, evidence hierarchy) are hardcoded and cannot be modified.
          </p>
        </div>
      </div>
    </div>
  );
}
