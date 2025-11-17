'use client';

import CustomInstructionsEditor from '../../../components/CustomInstructionsEditor';

export default function InstructionsPage() {
  return (
    <div style={{ padding: '2rem' }}>
      {/* Header */}
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '2rem', fontWeight: 700, color: '#1f2937', marginBottom: '0.5rem' }}>
          Custom Instructions
        </h1>
        <p style={{ color: '#6b7280' }}>
          Customize system prompts and instructions for AI responses
        </p>
      </div>

      {/* Editor */}
      <div style={{
        background: 'white',
        border: '1px solid #e5e7eb',
        borderRadius: '0.75rem',
        padding: '1.5rem'
      }}>
        <CustomInstructionsEditor />
      </div>
    </div>
  );
}
