'use client';

import { useState, useEffect } from 'react';
import { FileText, Save, Eye, History, Check, X, Plus, Trash2, RefreshCw, Edit2, Copy, AlertCircle } from 'lucide-react';
import { useInstructions, invalidateTuningCache, type CustomInstruction } from '@/hooks/useTuningData';
import { apiFetch } from '@/utils/api';

interface InstructionPreview {
  baseline_prompt: string;
  custom_instructions: string;
  merged_prompt: string;
  character_count: number;
  estimated_tokens: number;
}

interface InstructionHistory {
  id: number;
  instruction_id: number;
  instructions: string;
  version: number;
  changed_at: string;
}

export default function CustomInstructionsEditor() {
  const { data: instructions, loading: instructionsLoading, isUnauthorized, refresh: refreshInstructions } = useInstructions();
  const [activeInstruction, setActiveInstruction] = useState<CustomInstruction | null>(null);
  const [editMode, setEditMode] = useState(false);
  const [preview, setPreview] = useState<InstructionPreview | null>(null);
  const [history, setHistory] = useState<InstructionHistory[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState<'success' | 'error'>('success');
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Form state
  const [formData, setFormData] = useState<CustomInstruction>({
    name: '',
    instructions: '',
    description: '',
    is_active: false,
  });

  // Sync active instruction from hook data
  useEffect(() => {
    if (instructions) {
      const active = instructions.find((i) => i.is_active);
      if (active) {
        setActiveInstruction(active);
        setFormData(active);
      }
    }
  }, [instructions]);

  const loadHistory = async (instructionId: number) => {
    try {
      const res = await apiFetch(`/api/tuning/instructions/${instructionId}/history`);
      const data = await res.json();
      setHistory(data);
      setShowHistory(true);
    } catch (error) {
      showMessage('Failed to load history', 'error');
      console.error(error);
    }
  };

  const generatePreview = async () => {
    try {
      setLoading(true);
      const res = await apiFetch('/api/tuning/instructions/preview', {
        method: 'POST',
        body: JSON.stringify(formData),
      });
      const data = await res.json();
      setPreview(data);
    } catch (error) {
      showMessage('Failed to generate preview', 'error');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const saveInstructions = async () => {
    try {
      setLoading(true);
      
      const url = formData.id
        ? `/api/tuning/instructions/${formData.id}`
        : '/api/tuning/instructions';
      
      const method = formData.id ? 'PUT' : 'POST';
      
      const res = await apiFetch(url, {
        method,
        body: JSON.stringify(formData),
      });
      
      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'Failed to save');
      }
      
      const data = await res.json();
      showMessage('Instructions saved successfully!', 'success');
      setEditMode(false);
      invalidateTuningCache('instructions');
      refreshInstructions();
    } catch (error: any) {
      showMessage(error.message || 'Failed to save instructions', 'error');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const activateInstructions = async (id: number) => {
    try {
      setLoading(true);
      const res = await apiFetch(`/api/tuning/instructions/${id}/activate`, {
        method: 'POST',
      });
      const data = await res.json();
      showMessage(data.message, 'success');
      invalidateTuningCache('instructions');
      refreshInstructions();
    } catch (error) {
      showMessage('Failed to activate instructions', 'error');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const deleteInstructions = async (id: number) => {
    if (!confirm('Are you sure you want to delete this instruction set?')) {
      return;
    }
    
    try {
      setLoading(true);
      const res = await apiFetch(`/api/tuning/instructions/${id}`, {
        method: 'DELETE',
      });
      const data = await res.json();
      showMessage(data.message, 'success');
      invalidateTuningCache('instructions');
      refreshInstructions();
    } catch (error) {
      showMessage('Failed to delete instructions', 'error');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const rollbackToVersion = async (instructionId: number, version: number) => {
    if (!confirm(`Rollback to version ${version}?`)) {
      return;
    }
    
    try {
      setLoading(true);
      const res = await apiFetch(`/api/tuning/instructions/${instructionId}/rollback/${version}`, {
        method: 'POST',
      });
      const data = await res.json();
      showMessage(data.message, 'success');
      invalidateTuningCache('instructions');
      refreshInstructions();
      setShowHistory(false);
    } catch (error) {
      showMessage('Failed to rollback', 'error');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const showMessage = (msg: string, type: 'success' | 'error') => {
    setMessage(msg);
    setMessageType(type);
    setTimeout(() => setMessage(''), 5000);
  };

  const startNewInstruction = () => {
    setFormData({
      name: '',
      instructions: '',
      description: '',
      is_active: false,
    });
    setEditMode(true);
    setPreview(null);
  };

  const editInstruction = (instruction: CustomInstruction) => {
    setFormData(instruction);
    setEditMode(true);
    setPreview(null);
  };

  if (instructionsLoading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '3rem' }}>
        <p style={{ color: 'var(--text-muted, #6b7280)' }}>Loading instructions...</p>
      </div>
    );
  }

  if (isUnauthorized) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '3rem' }}>
        <AlertCircle style={{ width: 48, height: 48, opacity: 0.5, marginBottom: '1rem', color: 'var(--text-muted, #6b7280)' }} />
        <p style={{ color: 'var(--text-muted, #6b7280)' }}>Authentication required. Please log in again.</p>
      </div>
    );
  }

  return (
    <div className="custom-instructions-container" style={{
      background: 'var(--bg-card, #ffffff)',
      border: '1px solid var(--border-subtle, #e5e7eb)',
      borderRadius: '0.75rem',
      padding: '1.5rem'
    }}>
      <div className="ci-header" style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '1.5rem', gap: '1rem', flexWrap: 'wrap' }}>
        <div style={{ flex: '1 1 auto', minWidth: '200px' }}>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-primary, #1f2937)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <FileText style={{ width: '1.5rem', height: '1.5rem', color: 'var(--text-muted, #6b7280)' }} />
            Custom Instructions
          </h2>
          <p style={{ color: 'var(--text-muted, #6b7280)', fontSize: '0.875rem', marginTop: '0.25rem' }}>
            Add your own guidance without modifying core safety rules
          </p>
        </div>
        
        {!editMode && (
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
              onClick={async () => {
                setIsRefreshing(true);
                try {
                  await refreshInstructions();
                  showMessage('Configuration refreshed from server.', 'success');
                } catch {
                  showMessage('Could not refresh. Please try again.', 'error');
                } finally {
                  setIsRefreshing(false);
                }
              }}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                padding: '0.625rem',
                background: 'transparent',
                color: 'var(--text-muted, #6b7280)',
                border: '1px solid var(--border-subtle, #e5e7eb)',
                borderRadius: '0.5rem',
                cursor: isRefreshing ? 'not-allowed' : 'pointer',
                opacity: isRefreshing ? 0.5 : 1,
                transition: 'all 0.2s'
              }}
              disabled={isRefreshing}
              title="Refresh from server"
            >
              <RefreshCw style={{ width: '1rem', height: '1rem', animation: isRefreshing ? 'spin 1s linear infinite' : 'none' }} />
            </button>
            <button
              onClick={startNewInstruction}
              className="ci-new-btn"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                background: 'var(--accent, #000000)',
                color: 'var(--accent-foreground, white)',
                padding: '0.625rem 1rem',
                borderRadius: '0.5rem',
                border: 'none',
                fontWeight: 500,
                cursor: 'pointer',
                transition: 'background 0.2s',
                whiteSpace: 'nowrap'
              }}
              onMouseEnter={(e) => e.currentTarget.style.background = 'var(--accent-hover, #333333)'}
              onMouseLeave={(e) => e.currentTarget.style.background = 'var(--accent, #000000)'}
            >
              <Plus style={{ width: '1rem', height: '1rem' }} />
              New Instruction Set
            </button>
          </div>
        )}
      </div>

      {/* Message Banner */}
      {message && (
        <div style={{
          marginBottom: '1rem',
          padding: '0.75rem 1rem',
          borderRadius: '0.5rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          background: messageType === 'success' ? '#f0fdf4' : '#fef2f2',
          color: messageType === 'success' ? '#059669' : '#dc2626',
          border: `1px solid ${messageType === 'success' ? '#d1fae5' : '#fecaca'}`,
          fontSize: '0.875rem',
          fontWeight: 500
        }}>
          {messageType === 'success' ? <Check style={{ width: '1.25rem', height: '1.25rem' }} /> : <X style={{ width: '1.25rem', height: '1.25rem' }} />}
          {message}
        </div>
      )}

      {/* Edit Mode - Card-style form */}
      {editMode ? (
        <div style={{
          background: 'var(--bg-card, #ffffff)',
          border: '2px solid var(--accent, #000000)',
          borderRadius: '0.75rem',
          padding: '1.5rem 2rem'
        }}>
          {/* Header */}
          <div style={{ marginBottom: '2rem' }}>
            <h3 style={{ fontSize: '1.25rem', fontWeight: 600, color: 'var(--text-primary, #1f2937)', marginBottom: '0.5rem' }}>
              {formData.id ? 'Edit Instruction Set' : 'New Instruction Set'}
            </h3>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-muted, #6b7280)' }}>
              {formData.id ? 'Modify your custom instructions below' : 'Create a new set of custom instructions'}
            </p>
          </div>

          {/* Form fields with consistent spacing */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            {/* Name and Description row */}
            <div className="ci-form-row" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '1rem' }}>
              <div>
                <label className="ci-form-label" style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-primary, #e5e5e5)', marginBottom: '0.5rem' }}>
                  Name *
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g., 'Enhanced Medical Focus'"
                  maxLength={255}
                  className="ci-form-input"
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    border: '2px solid var(--border-subtle, #3a3a3a)',
                    borderRadius: '0.5rem',
                    fontSize: '1rem',
                    background: 'var(--bg-card-elevated, #1a1a1a)',
                    color: 'var(--text-primary, #f0f0f0)',
                    boxSizing: 'border-box'
                  }}
                />
              </div>
              
              <div>
                <label className="ci-form-label" style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-primary, #e5e5e5)', marginBottom: '0.5rem' }}>
                  Description
                </label>
                <input
                  type="text"
                  value={formData.description || ''}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="What these instructions do"
                  maxLength={500}
                  className="ci-form-input"
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    border: '2px solid var(--border-subtle, #3a3a3a)',
                    borderRadius: '0.5rem',
                    fontSize: '1rem',
                    background: 'var(--bg-card-elevated, #1a1a1a)',
                    color: 'var(--text-primary, #f0f0f0)',
                    boxSizing: 'border-box'
                  }}
                />
              </div>
            </div>

            {/* Custom Instructions textarea */}
            <div>
              <label className="ci-form-label" style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-primary, #e5e5e5)', marginBottom: '0.5rem' }}>
                Custom Instructions * <span style={{ fontWeight: 400, color: 'var(--text-muted, #a0a0a0)' }}>({formData.instructions.length}/10000)</span>
              </label>
              <textarea
                value={formData.instructions}
                onChange={(e) => setFormData({ ...formData, instructions: e.target.value })}
                placeholder="Add your custom guidance here. Examples:
- Emphasize specific topics
- Adjust tone or depth
- Add citation preferences
- Focus on particular health conditions"
                rows={10}
                maxLength={10000}
                className="ci-form-textarea"
                style={{
                  width: '100%',
                  padding: '1rem',
                  border: '2px solid var(--border-subtle, #3a3a3a)',
                  borderRadius: '0.5rem',
                  fontSize: '0.875rem',
                  fontFamily: 'monospace',
                  background: 'var(--bg-card-elevated, #1a1a1a)',
                  color: 'var(--text-primary, #f0f0f0)',
                  resize: 'vertical',
                  minHeight: '200px',
                  boxSizing: 'border-box'
                }}
              />
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted, #6b7280)', marginTop: '0.5rem' }}>
                These will be layered on top of baseline safety rules (which remain protected)
              </p>
            </div>

            {/* Activate checkbox */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <input
                type="checkbox"
                id="is_active"
                checked={formData.is_active}
                onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                className="ci-checkbox"
              />
              <label htmlFor="is_active" className="ci-form-label" style={{ fontSize: '0.875rem', cursor: 'pointer', marginBottom: 0 }}>
                Activate immediately after saving
              </label>
            </div>
          </div>

          {/* Buttons */}
          <div className="ci-buttons" style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', marginTop: '1.5rem' }}>
            <button
              onClick={saveInstructions}
              disabled={loading || !formData.name || !formData.instructions}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.75rem 1.5rem',
                background: loading || !formData.name || !formData.instructions ? '#9ca3af' : 'var(--accent, #000000)',
                color: 'var(--accent-foreground, white)',
                border: 'none',
                borderRadius: '0.5rem',
                fontWeight: 600,
                cursor: loading || !formData.name || !formData.instructions ? 'not-allowed' : 'pointer',
                transition: 'background 0.2s'
              }}
            >
              <Save style={{ width: '1rem', height: '1rem' }} />
              {formData.id ? 'Save Changes' : 'Create Instruction Set'}
            </button>
            
            <button
              onClick={generatePreview}
              disabled={loading || !formData.instructions}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.75rem 1.5rem',
                background: 'transparent',
                color: 'var(--text-primary, #374151)',
                border: '1px solid var(--border-subtle, #d1d5db)',
                borderRadius: '0.5rem',
                fontWeight: 500,
                cursor: loading || !formData.instructions ? 'not-allowed' : 'pointer',
                opacity: loading || !formData.instructions ? 0.5 : 1,
                transition: 'all 0.2s'
              }}
            >
              <Eye style={{ width: '1rem', height: '1rem' }} />
              Preview
            </button>
            
            <button
              onClick={() => {
                setEditMode(false);
                setPreview(null);
                refreshInstructions();
              }}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.75rem 1.5rem',
                background: 'transparent',
                color: 'var(--text-muted, #6b7280)',
                border: '1px solid var(--border-subtle, #e5e7eb)',
                borderRadius: '0.5rem',
                fontWeight: 500,
                cursor: 'pointer',
                transition: 'all 0.2s'
              }}
            >
              <X style={{ width: '1rem', height: '1rem' }} />
              Cancel
            </button>
          </div>

          {/* Preview */}
          {preview && (
            <div style={{
              marginTop: '1.5rem',
              border: '1px solid var(--border-subtle, #e5e7eb)',
              borderRadius: '0.5rem',
              padding: '1rem',
              background: 'var(--bg-card-elevated, #f9fafb)'
            }}>
              <h4 style={{ fontWeight: 600, marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-primary, #1f2937)' }}>
                <Eye style={{ width: '1.25rem', height: '1.25rem' }} />
                Merged Prompt Preview
              </h4>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-muted, #6b7280)', marginBottom: '0.75rem' }}>
                {preview.character_count} characters • ~{preview.estimated_tokens} tokens
              </p>
              <pre style={{
                background: 'var(--bg-card, #ffffff)',
                border: '1px solid var(--border-subtle, #e5e7eb)',
                borderRadius: '0.375rem',
                padding: '1rem',
                fontSize: '0.75rem',
                overflow: 'auto',
                whiteSpace: 'pre-wrap',
                maxHeight: '300px',
                color: 'var(--text-primary, #1f2937)'
              }}>
                {preview.merged_prompt}
              </pre>
            </div>
          )}
        </div>
      ) : (
        /* List Mode - Card Grid */
        <div className="ci-card-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1rem' }}>
          {(instructions || []).map((instruction) => (
            <div
              key={instruction.id}
              className={instruction.is_active ? 'ci-active-card' : ''}
              style={{
                background: instruction.is_active ? 'var(--ci-active-bg, #ecfdf5)' : 'var(--bg-card, #ffffff)',
                border: instruction.is_active ? '2px solid var(--ci-active-border, #34d399)' : '1px solid var(--border-subtle, #e5e7eb)',
                borderRadius: '0.75rem',
                padding: '1.25rem',
                display: 'flex',
                flexDirection: 'column',
                transition: 'all 0.2s',
                width: '100%',
                boxSizing: 'border-box',
                overflow: 'hidden'
              }}
            >
              {/* Card Header */}
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem', flexWrap: 'wrap' }}>
                    <h3 style={{ fontWeight: 600, fontSize: '1rem', color: 'var(--text-primary, #1f2937)' }}>{instruction.name}</h3>
                    {instruction.is_active && (
                      <span style={{
                        background: 'var(--ci-active-border, #34d399)',
                        color: '#052e16',
                        fontSize: '0.65rem',
                        padding: '0.2rem 0.5rem',
                        borderRadius: '9999px',
                        fontWeight: 600,
                        textTransform: 'uppercase',
                        letterSpacing: '0.025em'
                      }}>Active</span>
                    )}
                    {instruction.version && (
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted, #6b7280)' }}>v{instruction.version}</span>
                    )}
                  </div>
                  {instruction.description && (
                    <p style={{ fontSize: '0.8rem', color: instruction.is_active ? 'var(--ci-active-text, #065f46)' : 'var(--text-muted, #6b7280)', lineHeight: 1.4 }}>{instruction.description}</p>
                  )}
                </div>
                
                {/* Action Icons */}
                <div style={{ display: 'flex', gap: '0.25rem', marginLeft: '0.5rem' }}>
                  {instruction.id && instruction.id > 1 && (
                    <button
                      onClick={() => loadHistory(instruction.id!)}
                      style={{
                        background: 'transparent',
                        border: 'none',
                        padding: '0.375rem',
                        borderRadius: '0.375rem',
                        cursor: 'pointer',
                        color: 'var(--text-muted, #6b7280)',
                        transition: 'all 0.2s'
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background = 'var(--bg-card-elevated, #f3f4f6)';
                        e.currentTarget.style.color = 'var(--text-primary, #1f2937)';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = 'transparent';
                        e.currentTarget.style.color = 'var(--text-muted, #6b7280)';
                      }}
                      title="View History"
                    >
                      <History style={{ width: '1rem', height: '1rem' }} />
                    </button>
                  )}
                  
                  <button
                    onClick={() => editInstruction(instruction)}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      padding: '0.375rem',
                      borderRadius: '0.375rem',
                      cursor: 'pointer',
                      color: 'var(--text-muted, #6b7280)',
                      transition: 'all 0.2s'
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = 'var(--bg-card-elevated, #f3f4f6)';
                      e.currentTarget.style.color = 'var(--text-primary, #1f2937)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = 'transparent';
                      e.currentTarget.style.color = 'var(--text-muted, #6b7280)';
                    }}
                    title="Edit"
                  >
                    <Edit2 style={{ width: '1rem', height: '1rem' }} />
                  </button>
                  
                  {!instruction.is_active && instruction.name !== 'default' && instruction.id && (
                    <button
                      onClick={() => deleteInstructions(instruction.id!)}
                      style={{
                        background: 'transparent',
                        border: 'none',
                        padding: '0.375rem',
                        borderRadius: '0.375rem',
                        cursor: 'pointer',
                        color: 'var(--text-muted, #6b7280)',
                        transition: 'all 0.2s'
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background = '#fef2f2';
                        e.currentTarget.style.color = '#dc2626';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = 'transparent';
                        e.currentTarget.style.color = 'var(--text-muted, #6b7280)';
                      }}
                      title="Delete"
                    >
                      <Trash2 style={{ width: '1rem', height: '1rem' }} />
                    </button>
                  )}
                </div>
              </div>
              
              {/* Card Body - Instructions Preview */}
              <div style={{
                flex: 1,
                background: 'var(--bg-card-elevated, #f9fafb)',
                borderRadius: '0.5rem',
                padding: '0.75rem',
                marginBottom: '0.75rem',
                maxHeight: '8rem',
                overflowY: 'auto'
              }}>
                <pre style={{
                  fontSize: '0.75rem',
                  color: 'var(--text-muted, #4b5563)',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                  margin: 0,
                  fontFamily: 'ui-monospace, monospace',
                  lineHeight: 1.5
                }}>
                  {instruction.instructions || '(No custom instructions)'}
                </pre>
              </div>
              
              {/* Card Footer */}
              <div style={{ marginTop: 'auto' }}>
                {instruction.is_active ? (
                  <div style={{
                    width: '100%',
                    padding: '0.625rem',
                    background: 'var(--bg-card-elevated, #f3f4f6)',
                    color: 'var(--text-muted, #6b7280)',
                    borderRadius: '0.5rem',
                    fontWeight: 500,
                    textAlign: 'center',
                    fontSize: '0.875rem'
                  }}>
                    Currently active
                  </div>
                ) : (
                  <button
                    onClick={() => activateInstructions(instruction.id!)}
                    disabled={loading}
                    style={{
                      width: '100%',
                      padding: '0.625rem',
                      background: loading ? '#9ca3af' : 'var(--accent, #000000)',
                      color: 'var(--accent-foreground, white)',
                      border: 'none',
                      borderRadius: '0.5rem',
                      fontWeight: 500,
                      cursor: loading ? 'not-allowed' : 'pointer',
                      transition: 'background 0.2s',
                      fontSize: '0.875rem'
                    }}
                    onMouseEnter={(e) => {
                      if (!loading) e.currentTarget.style.background = 'var(--accent-hover, #333333)';
                    }}
                    onMouseLeave={(e) => {
                      if (!loading) e.currentTarget.style.background = 'var(--accent, #000000)';
                    }}
                  >
                    Activate This Set
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* History Modal - Cleaned up styling */}
      {showHistory && (
        <div style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(0, 0, 0, 0.6)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 50,
          padding: '1rem'
        }}>
          <div style={{
            background: 'var(--bg-card, #1a1a1a)',
            border: '1px solid var(--border-subtle, #333)',
            borderRadius: '0.75rem',
            padding: '1.5rem',
            maxWidth: '600px',
            width: '100%',
            maxHeight: '80vh',
            overflowY: 'auto'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
              <h3 style={{ fontSize: '1.125rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--text-primary)' }}>
                <History style={{ width: 20, height: 20, color: 'var(--text-muted)' }} />
                Version History
              </h3>
              <button
                onClick={() => setShowHistory(false)}
                style={{
                  background: 'transparent',
                  border: 'none',
                  padding: '0.5rem',
                  borderRadius: '0.375rem',
                  cursor: 'pointer',
                  color: 'var(--text-muted)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center'
                }}
              >
                <X style={{ width: 20, height: 20 }} />
              </button>
            </div>
            
            {history.length === 0 ? (
              <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '2rem 0' }}>
                No version history available.
              </p>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {history.map((h, index) => {
                  // Most recent version (index 0) gets highlighted styling
                  const isLatest = index === 0;
                  return (
                    <div key={h.id} style={{
                      border: isLatest ? '2px solid #22c55e' : '1px solid var(--border-subtle, #333)',
                      borderRadius: '0.5rem',
                      padding: '1rem',
                      background: isLatest ? 'rgba(34, 197, 94, 0.1)' : 'var(--bg-card-elevated, #0f0f0f)'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                          <span style={{
                            background: isLatest ? '#22c55e' : 'var(--bg-card, #262626)',
                            color: isLatest ? '#052e16' : 'var(--text-muted)',
                            fontSize: '0.75rem',
                            fontWeight: 600,
                            padding: '0.25rem 0.5rem',
                            borderRadius: '0.25rem'
                          }}>
                            v{h.version}{isLatest ? ' (Latest)' : ''}
                          </span>
                          <span style={{ fontSize: '0.8rem', color: isLatest ? '#166534' : 'var(--text-muted)' }}>
                            {new Date(h.changed_at).toLocaleDateString('en-US', { 
                              month: 'short', 
                              day: 'numeric', 
                              year: 'numeric',
                              hour: '2-digit',
                              minute: '2-digit'
                            })}
                          </span>
                        </div>
                        <button
                          onClick={() => rollbackToVersion(h.instruction_id, h.version)}
                          disabled={loading}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.35rem',
                            fontSize: '0.75rem',
                            fontWeight: 500,
                            background: isLatest ? '#166534' : 'var(--accent, #3b82f6)',
                            color: 'white',
                            padding: '0.35rem 0.75rem',
                            borderRadius: '0.375rem',
                            border: 'none',
                            cursor: loading ? 'not-allowed' : 'pointer',
                            opacity: loading ? 0.5 : 1,
                            transition: 'opacity 0.15s'
                          }}
                        >
                          <RefreshCw style={{ width: 12, height: 12 }} />
                          Restore
                        </button>
                      </div>
                      <p style={{
                        fontSize: '0.8rem',
                        color: isLatest ? '#166534' : 'var(--text-muted)',
                        background: isLatest ? 'rgba(34, 197, 94, 0.05)' : 'var(--bg-body, #0a0a0a)',
                        borderRadius: '0.375rem',
                        padding: '0.75rem',
                        margin: 0,
                        maxHeight: '80px',
                        overflowY: 'auto',
                        whiteSpace: 'pre-wrap',
                        wordBreak: 'break-word',
                        lineHeight: 1.5
                      }}>
                        {h.instructions.length > 160 
                          ? `${h.instructions.substring(0, 160)}...` 
                          : h.instructions || '(Empty instructions)'}
                      </p>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
