'use client';

import CustomInstructionsEditor from '../../../components/CustomInstructionsEditor';
import '../../../styles/custom-instructions.css';

export default function InstructionsPage() {
  return (
    <div className="tuning-page">
      {/* Header */}
      <div className="tuning-page-header">
        <h1 className="tuning-page-title">Custom Instructions</h1>
        <p className="tuning-page-description">
          Customize system prompts and instructions for AI responses
        </p>
      </div>

      {/* Editor */}
      <CustomInstructionsEditor />
    </div>
  );
}
