#!/usr/bin/env python3
"""
Test custom instructions layered prompt system
"""

import pytest
import sys
import os
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

# Add shared to path
shared_path = Path(__file__).parent.parent / "shared"
sys.path.insert(0, str(shared_path))

from prompts.prompt_loader import ChaffeePromptLoader


def test_baseline_prompt_loads():
    """Test that baseline prompt loads without custom instructions"""
    loader = ChaffeePromptLoader()
    baseline = loader.load_system_prompt(include_custom=False)
    
    assert baseline
    assert "Emulated Dr. Anthony Chaffee" in baseline
    assert "Voice & Priorities" in baseline
    assert "Content Rules" in baseline


def test_custom_instructions_merge():
    """Test that custom instructions merge with baseline"""
    loader = ChaffeePromptLoader()
    
    # Load with custom (may be empty if DB not configured)
    full_prompt = loader.load_system_prompt(include_custom=True)
    
    # Should at least have baseline
    assert full_prompt
    assert "Emulated Dr. Anthony Chaffee" in full_prompt


def test_prompt_structure():
    """Test that merged prompt has correct structure"""
    loader = ChaffeePromptLoader()
    baseline = loader.load_system_prompt(include_custom=False)
    
    # Baseline should have key sections
    assert "## Voice & Priorities" in baseline
    assert "## Content Rules" in baseline
    assert "## Output Contract" in baseline
    
    # Should not have custom section in baseline-only mode
    assert "## Additional Custom Instructions" not in baseline


def test_custom_instructions_optional():
    """Test that system works without custom instructions table"""
    loader = ChaffeePromptLoader()
    
    # Should not crash even if DB not available
    try:
        prompt = loader.load_system_prompt(include_custom=True)
        assert prompt  # Should have at least baseline
    except Exception as e:
        pytest.fail(f"Should not crash without custom instructions: {e}")


def test_schema_loading():
    """Test that response schema loads correctly"""
    loader = ChaffeePromptLoader()
    schema = loader.load_response_schema()
    
    assert schema
    assert "required" in schema
    assert "properties" in schema


def test_full_prompt_creation():
    """Test creating full OpenAI-compatible prompt"""
    loader = ChaffeePromptLoader()
    
    example_snippets = [
        {
            "text": "The carnivore diet eliminates all plant foods.",
            "video_id": "test123",
            "timestamp": "5:30",
            "title": "Carnivore Basics"
        }
    ]
    
    messages = loader.create_full_prompt(
        user_input="What is the carnivore diet?",
        chaffee_snippets=example_snippets,
        answer_mode="concise"
    )
    
    assert len(messages) == 2
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    
    # System message should have baseline
    assert "Emulated Dr. Anthony Chaffee" in messages[0]["content"]
    
    # User message should have query and context
    assert "What is the carnivore diet?" in messages[1]["content"]
    assert "Carnivore Basics" in messages[1]["content"]


if __name__ == "__main__":
    # Run tests
    print("Testing Custom Instructions System...")
    print("=" * 60)
    
    test_baseline_prompt_loads()
    print("✅ Baseline prompt loads")
    
    test_custom_instructions_merge()
    print("✅ Custom instructions merge")
    
    test_prompt_structure()
    print("✅ Prompt structure correct")
    
    test_custom_instructions_optional()
    print("✅ Custom instructions optional")
    
    test_schema_loading()
    print("✅ Schema loading works")
    
    test_full_prompt_creation()
    print("✅ Full prompt creation works")
    
    print("=" * 60)
    print("All tests passed! ✅")
