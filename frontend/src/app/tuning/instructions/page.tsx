'use client';

import CustomInstructionsEditor from '../../../components/CustomInstructionsEditor';
import '../../../styles/custom-instructions.css';
import '../tuning-pages.css';

export default function InstructionsPage() {
  return (
    <div className="tuning-page">
      {/* Header */}
      <div className="tuning-header">
        <h1 className="tuning-title">Custom Instructions</h1>
        <p className="tuning-text-muted">Customize system prompts and instructions for AI responses</p>
      </div>

      {/* Editor */}
      <CustomInstructionsEditor />
    </div>
  );
}
