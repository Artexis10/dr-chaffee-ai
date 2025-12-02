/**
 * Model type definitions for the RAG system
 */

export interface ModelCapabilities {
  json_mode: boolean;
  vision: boolean;
  max_context: number;
}

export interface RAGModelInfo {
  key: string;
  label: string;
  recommended: boolean;
  tags: string[];
  max_tokens: number;
  capabilities: ModelCapabilities;
}

export interface RagProfile {
  id?: string;
  name: string;
  description?: string;
  base_instructions: string;
  style_instructions?: string;
  retrieval_hints?: string;
  model_name: string;
  max_context_tokens: number;
  temperature: number;
  auto_select_model: boolean;
  version?: number;
  is_default: boolean;
  created_at?: string;
  updated_at?: string;
}

// Fallback models if API fails
export const FALLBACK_RAG_MODELS: RAGModelInfo[] = [
  {
    key: 'gpt-4.1',
    label: 'GPT-4.1 (Best quality)',
    max_tokens: 128000,
    recommended: true,
    tags: ['high-quality', 'json-mode', '128k'],
    capabilities: {
      json_mode: true,
      vision: false,
      max_context: 128000
    }
  },
  {
    key: 'gpt-4o-mini',
    label: 'GPT-4o Mini (Cheapest)',
    max_tokens: 128000,
    recommended: true,
    tags: ['fast', 'cheap', 'json-mode', '128k'],
    capabilities: {
      json_mode: true,
      vision: false,
      max_context: 128000
    }
  },
];
