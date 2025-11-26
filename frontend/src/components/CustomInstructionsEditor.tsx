'use client';

import { useState, useEffect } from 'react';
import { FileText, Save, Eye, History, Check, X, Plus, Trash2, RefreshCw, Edit2, Copy } from 'lucide-react';

interface CustomInstruction {
  id?: number;
  name: string;
  instructions: string;
  description?: string;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
  version?: number;
}

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
  const [instructions, setInstructions] = useState<CustomInstruction[]>([]);
  const [activeInstruction, setActiveInstruction] = useState<CustomInstruction | null>(null);
  const [editMode, setEditMode] = useState(false);
  const [preview, setPreview] = useState<InstructionPreview | null>(null);
  const [history, setHistory] = useState<InstructionHistory[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState<'success' | 'error'>('success');

  // Form state
  const [formData, setFormData] = useState<CustomInstruction>({
    name: '',
    instructions: '',
    description: '',
    is_active: false,
  });

  useEffect(() => {
    loadInstructions();
  }, []);

  const loadInstructions = async () => {
    try {
      const res = await fetch('/api/tuning/instructions');
      const data = await res.json();
      setInstructions(data);
      
      // Find active instruction
      const active = data.find((i: CustomInstruction) => i.is_active);
      if (active) {
        setActiveInstruction(active);
        setFormData(active);
      }
    } catch (error) {
      showMessage('Failed to load instructions', 'error');
      console.error(error);
    }
  };

  const loadHistory = async (instructionId: number) => {
    try {
      const res = await fetch(`/api/tuning/instructions/${instructionId}/history`);
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
      const res = await fetch('/api/tuning/instructions/preview', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
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
      
      const res = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData),
      });
      
      if (!res.ok) {
        const error = await res.json();
        throw new Error(error.detail || 'Failed to save');
      }
      
      const data = await res.json();
      showMessage('Instructions saved successfully!', 'success');
      setEditMode(false);
      loadInstructions();
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
      const res = await fetch(`/api/tuning/instructions/${id}/activate`, {
        method: 'POST',
      });
      const data = await res.json();
      showMessage(data.message, 'success');
      loadInstructions();
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
      const res = await fetch(`/api/tuning/instructions/${id}`, {
        method: 'DELETE',
      });
      const data = await res.json();
      showMessage(data.message, 'success');
      loadInstructions();
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
      const res = await fetch(`/api/tuning/instructions/${instructionId}/rollback/${version}`, {
        method: 'POST',
      });
      const data = await res.json();
      showMessage(data.message, 'success');
      loadInstructions();
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

  return (
    <div style={{
      background: 'var(--bg-card, #ffffff)',
      border: '1px solid var(--border-subtle, #e5e7eb)',
      borderRadius: '0.75rem',
      padding: '1.5rem'
    }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem' }}>
        <div>
          <h2 style={{ fontSize: '1.5rem', fontWeight: 700, color: 'var(--text-primary, #1f2937)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <FileText style={{ width: '1.5rem', height: '1.5rem', color: 'var(--text-muted, #6b7280)' }} />
            Custom Instructions
          </h2>
          <p style={{ color: 'var(--text-muted, #6b7280)', fontSize: '0.875rem', marginTop: '0.25rem' }}>
            Add your own guidance without modifying core safety rules
          </p>
        </div>
        
        {!editMode && (
          <button
            onClick={startNewInstruction}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              background: 'var(--accent, #000000)',
              color: 'var(--accent-foreground, white)',
              padding: '0.5rem 1rem',
              borderRadius: '0.5rem',
              border: 'none',
              fontWeight: 500,
              cursor: 'pointer',
              transition: 'background 0.2s'
            }}
            onMouseEnter={(e) => e.currentTarget.style.background = 'var(--accent-hover, #333333)'}
            onMouseLeave={(e) => e.currentTarget.style.background = 'var(--accent, #000000)'}
          >
            <Plus style={{ width: '1rem', height: '1rem' }} />
            New Instruction Set
          </button>
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
          padding: '1.5rem'
        }}>
          <div style={{ marginBottom: '1.5rem' }}>
            <h3 style={{ fontSize: '1.125rem', fontWeight: 600, color: 'var(--text-primary, #1f2937)', marginBottom: '0.25rem' }}>
              {formData.id ? 'Edit Instruction Set' : 'New Instruction Set'}
            </h3>
            <p style={{ fontSize: '0.875rem', color: 'var(--text-muted, #6b7280)' }}>
              {formData.id ? 'Modify your custom instructions below' : 'Create a new set of custom instructions'}
            </p>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-primary, #374151)', marginBottom: '0.5rem' }}>
                Name *
              </label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="e.g., 'Enhanced Medical Focus'"
                maxLength={255}
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '1px solid var(--border-subtle, #d1d5db)',
                  borderRadius: '0.5rem',
                  fontSize: '1rem',
                  background: 'var(--bg-card-elevated, #f9fafb)',
                  color: 'var(--text-primary, #1f2937)'
                }}
              />
            </div>
            
            <div>
              <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-primary, #374151)', marginBottom: '0.5rem' }}>
                Description
              </label>
              <input
                type="text"
                value={formData.description || ''}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="What these instructions do"
                maxLength={500}
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  border: '1px solid var(--border-subtle, #d1d5db)',
                  borderRadius: '0.5rem',
                  fontSize: '1rem',
                  background: 'var(--bg-card-elevated, #f9fafb)',
                  color: 'var(--text-primary, #1f2937)'
                }}
              />
            </div>
          </div>

          <div style={{ marginBottom: '1rem' }}>
            <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-primary, #374151)', marginBottom: '0.5rem' }}>
              Custom Instructions * <span style={{ fontWeight: 400, color: 'var(--text-muted, #6b7280)' }}>({formData.instructions.length}/10000)</span>
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
              style={{
                width: '100%',
                padding: '0.75rem',
                border: '1px solid var(--border-subtle, #d1d5db)',
                borderRadius: '0.5rem',
                fontSize: '0.875rem',
                fontFamily: 'monospace',
                background: 'var(--bg-card-elevated, #f9fafb)',
                color: 'var(--text-primary, #1f2937)',
                resize: 'vertical',
                minHeight: '200px'
              }}
            />
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted, #6b7280)', marginTop: '0.5rem' }}>
              These will be layered on top of baseline safety rules (which remain protected)
            </p>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.5rem' }}>
            <input
              type="checkbox"
              id="is_active"
              checked={formData.is_active}
              onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
              style={{ width: '1rem', height: '1rem', cursor: 'pointer' }}
            />
            <label htmlFor="is_active" style={{ fontSize: '0.875rem', color: 'var(--text-primary, #374151)', cursor: 'pointer' }}>
              Activate immediately after saving
            </label>
          </div>

          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
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
                loadInstructions();
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
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '1rem' }}>
          {instructions.map((instruction) => (
            <div
              key={instruction.id}
              style={{
                background: instruction.is_active ? '#f0fdf4' : 'var(--bg-card, #ffffff)',
                border: instruction.is_active ? '2px solid #86efac' : '1px solid var(--border-subtle, #e5e7eb)',
                borderRadius: '0.75rem',
                padding: '1.25rem',
                display: 'flex',
                flexDirection: 'column',
                minHeight: '260px',
                transition: 'all 0.2s'
              }}
            >
              {/* Card Header */}
              <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem', flexWrap: 'wrap' }}>
                    <h3 style={{ fontWeight: 600, fontSize: '1rem', color: 'var(--text-primary, #1f2937)' }}>{instruction.name}</h3>
                    {instruction.is_active && (
                      <span style={{
                        background: '#1f2937',
                        color: 'white',
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
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-muted, #6b7280)', lineHeight: 1.4 }}>{instruction.description}</p>
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

      {/* History Modal */}
      {showHistory && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-slate-800 border border-slate-700 rounded-xl p-6 max-w-2xl w-full max-h-[80vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-bold flex items-center gap-2">
                <History className="w-5 h-5 text-blue-400" />
                Version History
              </h3>
              <button
                onClick={() => setShowHistory(false)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-6 h-6" />
              </button>
            </div>
            
            <div className="space-y-3">
              {history.map((h) => (
                <div key={h.id} className="border border-slate-600 rounded-lg p-4 bg-slate-900/50">
                  <div className="flex items-center justify-between mb-2">
                    <div className="text-sm">
                      <span className="font-semibold">Version {h.version}</span>
                      <span className="text-slate-400 ml-2">
                        {new Date(h.changed_at).toLocaleString()}
                      </span>
                    </div>
                    <button
                      onClick={() => rollbackToVersion(h.instruction_id, h.version)}
                      disabled={loading}
                      className="flex items-center gap-1 text-xs bg-blue-600 hover:bg-blue-700 disabled:bg-slate-600 text-white px-3 py-1 rounded transition-colors"
                    >
                      <RefreshCw className="w-3 h-3" />
                      Rollback
                    </button>
                  </div>
                  <pre className="text-xs text-slate-300 bg-slate-950 rounded p-3 max-h-32 overflow-y-auto whitespace-pre-wrap">
                    {h.instructions}
                  </pre>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
