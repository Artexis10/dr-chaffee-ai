'use client';

import CustomInstructionsEditor from '../../../components/CustomInstructionsEditor';
import '../../styles/custom-instructions.css';

export default function InstructionsPage() {
  return (
    <div style={{ padding: '2rem', background: '#fafafa', minHeight: '100vh' }}>
      {/* Header */}
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '2rem', fontWeight: 700, color: '#000000', marginBottom: '0.5rem' }}>
          Custom Instructions
        </h1>
        <p style={{ color: '#6b7280', fontSize: '1rem' }}>
          Customize system prompts and instructions for AI responses
        </p>
      </div>

      {/* Editor */}
      <CustomInstructionsEditor />
    </div>
  );
}
