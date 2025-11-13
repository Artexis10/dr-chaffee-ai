#!/usr/bin/env python3
"""
Prompt Loading Utility for Emulated Dr. Chaffee AI
Loads and formats prompts for consistent use across the application

Supports layered instruction system:
- Baseline: Core persona and safety rules (always included)
- Custom: User-defined instructions from database (optional layer)
"""

import os
import json
from typing import Dict, Any, List, Optional
from pathlib import Path
import psycopg2
from psycopg2.extras import RealDictCursor


class ChaffeePromptLoader:
    """Utility class for loading and formatting Dr. Chaffee AI prompts"""
    
    def __init__(self, prompts_dir: Optional[str] = None):
        if prompts_dir is None:
            # Default to shared/prompts relative to this file
            self.prompts_dir = Path(__file__).parent
        else:
            self.prompts_dir = Path(prompts_dir)
    
    def load_system_prompt(self, include_custom: bool = True) -> str:
        """
        Load the system prompt for Dr. Chaffee persona
        
        Args:
            include_custom: If True, merge active custom instructions from database
        
        Returns:
            Complete system prompt (baseline + custom if enabled)
        """
        persona_file = self.prompts_dir / "chaffee_persona.md"
        try:
            with open(persona_file, 'r', encoding='utf-8') as f:
                baseline_prompt = f.read().strip()
        except FileNotFoundError:
            raise FileNotFoundError(f"System prompt not found at {persona_file}")
        
        # If custom instructions disabled, return baseline only
        if not include_custom:
            return baseline_prompt
        
        # Try to load custom instructions from database
        try:
            custom_instructions = self._load_custom_instructions()
            if custom_instructions:
                return f"{baseline_prompt}\n\n## Additional Custom Instructions\n\n{custom_instructions}"
        except Exception as e:
            # Log but don't fail - fallback to baseline
            import logging
            logging.warning(f"Failed to load custom instructions, using baseline only: {e}")
        
        return baseline_prompt
    
    def _load_custom_instructions(self) -> Optional[str]:
        """
        Load active custom instructions from database
        
        Returns:
            Custom instructions text or None if not found/configured
        """
        database_url = os.getenv('DATABASE_URL')
        if not database_url:
            return None
        
        try:
            conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
            cur = conn.cursor()
            
            cur.execute("""
                SELECT instructions
                FROM custom_instructions
                WHERE is_active = true
                LIMIT 1
            """)
            
            result = cur.fetchone()
            cur.close()
            conn.close()
            
            if result and result['instructions'].strip():
                return result['instructions'].strip()
            
            return None
            
        except Exception as e:
            # Table might not exist yet (pre-migration)
            import logging
            logging.debug(f"Could not load custom instructions: {e}")
            return None
    
    def load_response_schema(self) -> Dict[str, Any]:
        """Load the JSON schema for response structure"""
        schema_file = self.prompts_dir / "chaffee_developer_schema.json"
        try:
            with open(schema_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"Response schema not found at {schema_file}")
    
    def load_user_template(self) -> str:
        """Load the user prompt template"""
        template_file = self.prompts_dir / "user_template.md"
        try:
            with open(template_file, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except FileNotFoundError:
            raise FileNotFoundError(f"User template not found at {template_file}")
    
    def format_user_prompt(
        self,
        user_input: str,
        chaffee_snippets: List[Dict[str, Any]],
        primary_studies: Optional[List[str]] = None,
        answer_mode: str = "expanded"
    ) -> str:
        """
        Format the user prompt with actual data
        
        Args:
            user_input: User's question
            chaffee_snippets: List of dicts with 'text', 'video_id', 'timestamp', 'title'
            primary_studies: Optional list of study excerpts
            answer_mode: Response mode (concise/expanded/deep_dive)
        """
        template = self.load_user_template()
        
        # Format Chaffee snippets
        chaffee_context = ""
        for i, snippet in enumerate(chaffee_snippets, 1):
            video_id = snippet.get('video_id', 'unknown')
            timestamp = snippet.get('timestamp', '0:00')
            title = snippet.get('title', 'Unknown Video')
            text = snippet.get('text', '')
            
            chaffee_context += f"{i}. [{title} - {video_id} @ {timestamp}]: {text}\n\n"
        
        # Format primary studies
        studies_context = ""
        if primary_studies:
            for i, study in enumerate(primary_studies, 1):
                studies_context += f"{i}. {study}\n\n"
        else:
            studies_context = "[No primary studies provided]"
        
        # Replace template variables
        formatted_prompt = template.replace("<<<{USER_INPUT}>>>", user_input)
        formatted_prompt = formatted_prompt.replace(
            "<<<{TOP_K_SNIPPETS_WITH_TIMESTAMPS_AND_SPEAKER=\"CHAFFEE\"}>>>", 
            chaffee_context.strip()
        )
        formatted_prompt = formatted_prompt.replace(
            "<<<{PRIMARY_STUDY_EXCERPTS}>>>", 
            studies_context.strip()
        )
        
        # Add answer mode instruction
        formatted_prompt += f"\n\n**Required Answer Mode**: {answer_mode}"
        
        return formatted_prompt
    
    def get_schema_instruction(self) -> str:
        """Get formatted schema instruction for the AI"""
        schema = self.load_response_schema()
        return f"""
You must respond with valid JSON that conforms to this exact schema:

{json.dumps(schema, indent=2)}

Required fields: {', '.join(schema['required'])}
Never omit any required fields. Always validate your JSON before responding.
"""
    
    def create_full_prompt(
        self,
        user_input: str,
        chaffee_snippets: List[Dict[str, Any]],
        primary_studies: Optional[List[str]] = None,
        answer_mode: str = "expanded"
    ) -> List[Dict[str, str]]:
        """
        Create full OpenAI-compatible message format
        
        Returns:
            List of message dicts for OpenAI API
        """
        system_prompt = self.load_system_prompt()
        schema_instruction = self.get_schema_instruction()
        user_prompt = self.format_user_prompt(
            user_input, chaffee_snippets, primary_studies, answer_mode
        )
        
        return [
            {
                "role": "system",
                "content": f"{system_prompt}\n\n{schema_instruction}"
            },
            {
                "role": "user", 
                "content": user_prompt
            }
        ]


# Example usage and testing
if __name__ == "__main__":
    # Example usage
    loader = ChaffeePromptLoader()
    
    # Test loading individual components
    print("=== System Prompt ===")
    print(loader.load_system_prompt()[:200] + "...")
    
    print("\n=== Schema Keys ===")
    schema = loader.load_response_schema()
    print(f"Required fields: {schema['required']}")
    
    print("\n=== User Template Preview ===")
    template = loader.load_user_template()
    print(template[:300] + "...")
    
    # Test full prompt creation
    example_snippets = [
        {
            "text": "The carnivore diet is the most species-appropriate diet for humans.",
            "video_id": "abc123",
            "timestamp": "12:34",
            "title": "Why Carnivore Works"
        }
    ]
    
    messages = loader.create_full_prompt(
        user_input="What does Dr. Chaffee think about the carnivore diet?",
        chaffee_snippets=example_snippets,
        answer_mode="expanded"
    )
    
    print(f"\n=== Full Prompt Created ===")
    print(f"System message length: {len(messages[0]['content'])}")
    print(f"User message length: {len(messages[1]['content'])}")
