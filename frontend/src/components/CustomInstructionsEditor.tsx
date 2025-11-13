'use client';

import { useState, useEffect } from 'react';
import { FileText, Save, Eye, History, Check, X, Plus, Trash2, RefreshCw } from 'lucide-react';

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
    <div className="bg-slate-800/50 backdrop-blur border border-slate-700 rounded-xl p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <FileText className="w-6 h-6 text-blue-400" />
            Custom Instructions
          </h2>
          <p className="text-slate-400 text-sm mt-1">
            Add your own guidance without modifying core safety rules
          </p>
        </div>
        
        {!editMode && (
          <button
            onClick={startNewInstruction}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition-colors"
          >
            <Plus className="w-4 h-4" />
            New Instruction Set
          </button>
        )}
      </div>

      {/* Message Banner */}
      {message && (
        <div className={`mb-4 p-4 rounded-lg flex items-center gap-2 ${
          messageType === 'success' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
        }`}>
          {messageType === 'success' ? <Check className="w-5 h-5" /> : <X className="w-5 h-5" />}
          {message}
        </div>
      )}

      {/* Edit Mode */}
      {editMode ? (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium mb-2">Name</label>
              <input
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="e.g., 'Enhanced Medical Focus'"
                className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2 focus:border-blue-500 focus:outline-none"
                maxLength={255}
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium mb-2">Description</label>
              <input
                type="text"
                value={formData.description || ''}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="What these instructions do"
                className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2 focus:border-blue-500 focus:outline-none"
                maxLength={500}
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium mb-2">
              Custom Instructions ({formData.instructions.length}/5000 characters)
            </label>
            <textarea
              value={formData.instructions}
              onChange={(e) => setFormData({ ...formData, instructions: e.target.value })}
              placeholder="Add your custom guidance here. Examples:&#10;- Emphasize specific topics&#10;- Adjust tone or depth&#10;- Add citation preferences&#10;- Focus on particular health conditions"
              className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-3 focus:border-blue-500 focus:outline-none font-mono text-sm"
              rows={12}
              maxLength={5000}
            />
            <p className="text-xs text-slate-400 mt-1">
              These will be layered on top of baseline safety rules (which remain protected)
            </p>
          </div>

          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="is_active"
              checked={formData.is_active}
              onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
              className="w-4 h-4 rounded"
            />
            <label htmlFor="is_active" className="text-sm">
              Activate immediately after saving
            </label>
          </div>

          <div className="flex gap-3">
            <button
              onClick={saveInstructions}
              disabled={loading || !formData.name || !formData.instructions}
              className="flex items-center gap-2 bg-green-600 hover:bg-green-700 disabled:bg-slate-600 text-white px-6 py-2 rounded-lg transition-colors"
            >
              <Save className="w-4 h-4" />
              Save Instructions
            </button>
            
            <button
              onClick={generatePreview}
              disabled={loading}
              className="flex items-center gap-2 bg-purple-600 hover:bg-purple-700 disabled:bg-slate-600 text-white px-6 py-2 rounded-lg transition-colors"
            >
              <Eye className="w-4 h-4" />
              Preview Merged Prompt
            </button>
            
            <button
              onClick={() => {
                setEditMode(false);
                setPreview(null);
                loadInstructions();
              }}
              className="flex items-center gap-2 bg-slate-600 hover:bg-slate-700 text-white px-6 py-2 rounded-lg transition-colors"
            >
              <X className="w-4 h-4" />
              Cancel
            </button>
          </div>

          {/* Preview */}
          {preview && (
            <div className="border border-slate-600 rounded-lg p-4 bg-slate-900/50">
              <h3 className="font-semibold mb-2 flex items-center gap-2">
                <Eye className="w-5 h-5 text-purple-400" />
                Merged Prompt Preview
              </h3>
              <div className="text-sm text-slate-400 mb-3">
                {preview.character_count} characters • ~{preview.estimated_tokens} tokens
              </div>
              <pre className="bg-slate-950 border border-slate-700 rounded p-4 text-xs overflow-x-auto whitespace-pre-wrap max-h-96 overflow-y-auto">
                {preview.merged_prompt}
              </pre>
            </div>
          )}
        </div>
      ) : (
        /* List Mode */
        <div className="space-y-4">
          {instructions.map((instruction) => (
            <div
              key={instruction.id}
              className={`border rounded-lg p-4 transition-all ${
                instruction.is_active
                  ? 'border-green-500 bg-green-500/10'
                  : 'border-slate-600 bg-slate-800/30'
              }`}
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-semibold text-lg">{instruction.name}</h3>
                    {instruction.is_active && (
                      <span className="bg-green-500 text-white text-xs px-2 py-1 rounded">Active</span>
                    )}
                    {instruction.version && (
                      <span className="text-xs text-slate-400">v{instruction.version}</span>
                    )}
                  </div>
                  {instruction.description && (
                    <p className="text-sm text-slate-400">{instruction.description}</p>
                  )}
                </div>
                
                <div className="flex gap-2">
                  {instruction.id && instruction.id > 1 && (
                    <button
                      onClick={() => loadHistory(instruction.id!)}
                      className="text-slate-400 hover:text-blue-400 transition-colors"
                      title="View History"
                    >
                      <History className="w-5 h-5" />
                    </button>
                  )}
                  
                  <button
                    onClick={() => editInstruction(instruction)}
                    className="text-slate-400 hover:text-yellow-400 transition-colors"
                    title="Edit"
                  >
                    <FileText className="w-5 h-5" />
                  </button>
                  
                  {!instruction.is_active && instruction.name !== 'default' && instruction.id && (
                    <button
                      onClick={() => deleteInstructions(instruction.id!)}
                      className="text-slate-400 hover:text-red-400 transition-colors"
                      title="Delete"
                    >
                      <Trash2 className="w-5 h-5" />
                    </button>
                  )}
                </div>
              </div>
              
              <div className="bg-slate-900/50 rounded p-3 mb-3 max-h-32 overflow-y-auto">
                <pre className="text-xs text-slate-300 whitespace-pre-wrap">
                  {instruction.instructions || '(No custom instructions)'}
                </pre>
              </div>
              
              {!instruction.is_active && (
                <button
                  onClick={() => activateInstructions(instruction.id!)}
                  disabled={loading}
                  className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-slate-600 text-white px-4 py-2 rounded-lg transition-colors"
                >
                  Activate This Set
                </button>
              )}
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
