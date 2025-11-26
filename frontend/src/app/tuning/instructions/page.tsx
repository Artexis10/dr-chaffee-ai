'use client';

import CustomInstructionsEditor from '../../../components/CustomInstructionsEditor';
import '../../../styles/custom-instructions.css';

export default function InstructionsPage() {
  return (
    <div className="p-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-1">
          Custom Instructions
        </h1>
        <p className="text-gray-500 dark:text-gray-400">
          Customize system prompts and instructions for AI responses
        </p>
      </div>

      {/* Editor */}
      <CustomInstructionsEditor />
    </div>
  );
}
