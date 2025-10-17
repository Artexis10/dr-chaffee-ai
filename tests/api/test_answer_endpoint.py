#!/usr/bin/env python3
"""
Unit tests for /answer endpoint
Tests RAG answer generation with mocked OpenAI responses
"""

import pytest
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'backend'))

from api.main import app

client = TestClient(app)


class TestAnswerEndpoint:
    """Test suite for /answer endpoint"""
    
    def test_answer_post_success(self):
        """Test POST /answer with valid request"""
        with patch('api.main.semantic_search') as mock_search, \
             patch('api.main.os.getenv') as mock_getenv, \
             patch('api.main.OpenAI') as mock_openai:
            
            # Mock environment variable
            mock_getenv.return_value = 'sk-test-key'
            
            # Mock search results
            mock_result = Mock()
            mock_result.id = 1
            mock_result.title = "Test Video"
            mock_result.text = "Carnivore diet is beneficial"
            mock_result.url = "https://youtube.com/watch?v=test"
            mock_result.start_time_seconds = 100.0
            mock_result.similarity = 0.85
            
            mock_search_response = Mock()
            mock_search_response.results = [mock_result]
            mock_search.return_value = mock_search_response
            
            # Mock OpenAI response
            mock_completion = Mock()
            mock_completion.choices = [Mock(message=Mock(content="Based on Dr. Chaffee's content..."))]
            mock_completion.usage = Mock(prompt_tokens=1000, completion_tokens=500)
            
            mock_client = Mock()
            mock_client.chat.completions.create.return_value = mock_completion
            mock_openai.return_value = mock_client
            
            # Make request
            response = client.post(
                "/answer",
                json={"query": "carnivore diet benefits", "top_k": 10}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "answer" in data
            assert "sources" in data
            assert "cost_usd" in data
            assert data["query"] == "carnivore diet benefits"
    
    def test_answer_get_success(self):
        """Test GET /answer with query parameters"""
        with patch('api.main.semantic_search') as mock_search, \
             patch('api.main.os.getenv') as mock_getenv, \
             patch('api.main.OpenAI') as mock_openai:
            
            mock_getenv.return_value = 'sk-test-key'
            
            # Mock search results
            mock_result = Mock()
            mock_result.id = 1
            mock_result.title = "Test Video"
            mock_result.text = "Carnivore diet is beneficial"
            mock_result.url = "https://youtube.com/watch?v=test"
            mock_result.start_time_seconds = 100.0
            mock_result.similarity = 0.85
            
            mock_search_response = Mock()
            mock_search_response.results = [mock_result]
            mock_search.return_value = mock_search_response
            
            # Mock OpenAI
            mock_completion = Mock()
            mock_completion.choices = [Mock(message=Mock(content="Answer text"))]
            mock_completion.usage = Mock(prompt_tokens=1000, completion_tokens=500)
            
            mock_client = Mock()
            mock_client.chat.completions.create.return_value = mock_completion
            mock_openai.return_value = mock_client
            
            # Make request
            response = client.get("/answer?query=carnivore+diet&top_k=5&style=concise")
            
            assert response.status_code == 200
            data = response.json()
            assert "answer" in data
    
    def test_answer_missing_api_key(self):
        """Test /answer returns 503 when OPENAI_API_KEY is missing"""
        with patch('api.main.semantic_search') as mock_search, \
             patch('api.main.os.getenv') as mock_getenv:
            
            # Mock missing API key
            mock_getenv.return_value = None
            
            # Mock search results
            mock_result = Mock()
            mock_result.id = 1
            mock_result.title = "Test Video"
            mock_result.text = "Test content"
            mock_result.url = "https://youtube.com/watch?v=test"
            mock_result.start_time_seconds = 100.0
            mock_result.similarity = 0.85
            
            mock_search_response = Mock()
            mock_search_response.results = [mock_result]
            mock_search.return_value = mock_search_response
            
            # Make request
            response = client.post(
                "/answer",
                json={"query": "test query", "top_k": 10}
            )
            
            assert response.status_code == 503
            data = response.json()
            assert "OpenAI API key not configured" in data["detail"]
    
    def test_answer_no_search_results(self):
        """Test /answer returns 404 when no search results found"""
        with patch('api.main.semantic_search') as mock_search:
            
            # Mock empty search results
            mock_search_response = Mock()
            mock_search_response.results = []
            mock_search.return_value = mock_search_response
            
            # Make request
            response = client.post(
                "/answer",
                json={"query": "nonexistent topic", "top_k": 10}
            )
            
            assert response.status_code == 404
            data = response.json()
            assert "No relevant information found" in data["detail"]
    
    def test_answer_builds_correct_context(self):
        """Test that answer endpoint builds correct RAG context"""
        with patch('api.main.semantic_search') as mock_search, \
             patch('api.main.os.getenv') as mock_getenv, \
             patch('api.main.OpenAI') as mock_openai:
            
            mock_getenv.return_value = 'sk-test-key'
            
            # Mock multiple search results
            results = []
            for i in range(3):
                mock_result = Mock()
                mock_result.id = i
                mock_result.title = f"Video {i}"
                mock_result.text = f"Content {i}"
                mock_result.url = f"https://youtube.com/watch?v=test{i}"
                mock_result.start_time_seconds = float(i * 100)
                mock_result.similarity = 0.9 - (i * 0.1)
                results.append(mock_result)
            
            mock_search_response = Mock()
            mock_search_response.results = results
            mock_search.return_value = mock_search_response
            
            # Mock OpenAI
            mock_completion = Mock()
            mock_completion.choices = [Mock(message=Mock(content="Answer"))]
            mock_completion.usage = Mock(prompt_tokens=1000, completion_tokens=500)
            
            mock_client = Mock()
            mock_client.chat.completions.create.return_value = mock_completion
            mock_openai.return_value = mock_client
            
            # Make request
            response = client.post(
                "/answer",
                json={"query": "test", "top_k": 10}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Should have 3 sources
            assert len(data["sources"]) == 3
            assert data["chunks_used"] == 3
            
            # Verify OpenAI was called with correct prompt structure
            call_args = mock_client.chat.completions.create.call_args
            messages = call_args[1]["messages"]
            prompt = messages[0]["content"]
            
            # Check prompt contains context from all results
            assert "Video 0" in prompt
            assert "Video 1" in prompt
            assert "Video 2" in prompt
            assert "Content 0" in prompt
            assert "Content 1" in prompt
            assert "Content 2" in prompt
    
    def test_answer_cost_calculation(self):
        """Test that cost is calculated correctly"""
        with patch('api.main.semantic_search') as mock_search, \
             patch('api.main.os.getenv') as mock_getenv, \
             patch('api.main.OpenAI') as mock_openai:
            
            mock_getenv.return_value = 'sk-test-key'
            
            # Mock search result
            mock_result = Mock()
            mock_result.id = 1
            mock_result.title = "Test"
            mock_result.text = "Content"
            mock_result.url = "https://youtube.com/watch?v=test"
            mock_result.start_time_seconds = 100.0
            mock_result.similarity = 0.85
            
            mock_search_response = Mock()
            mock_search_response.results = [mock_result]
            mock_search.return_value = mock_search_response
            
            # Mock OpenAI with specific token counts
            mock_completion = Mock()
            mock_completion.choices = [Mock(message=Mock(content="Answer"))]
            mock_completion.usage = Mock(
                prompt_tokens=2000,  # Input
                completion_tokens=500  # Output
            )
            
            mock_client = Mock()
            mock_client.chat.completions.create.return_value = mock_completion
            mock_openai.return_value = mock_client
            
            # Make request
            response = client.post(
                "/answer",
                json={"query": "test", "top_k": 10}
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Cost calculation: (2000 * 0.01 + 500 * 0.03) / 1000
            # = (20 + 15) / 1000 = 0.035
            expected_cost = (2000 * 0.01 + 500 * 0.03) / 1000
            assert abs(data["cost_usd"] - expected_cost) < 0.0001
    
    def test_answer_uses_correct_model(self):
        """Test that answer endpoint uses configured OpenAI model"""
        with patch('api.main.semantic_search') as mock_search, \
             patch('api.main.os.getenv') as mock_getenv, \
             patch('api.main.OpenAI') as mock_openai:
            
            def getenv_side_effect(key, default=None):
                if key == 'OPENAI_API_KEY':
                    return 'sk-test-key'
                elif key == 'OPENAI_MODEL':
                    return 'gpt-4o'
                return default
            
            mock_getenv.side_effect = getenv_side_effect
            
            # Mock search result
            mock_result = Mock()
            mock_result.id = 1
            mock_result.title = "Test"
            mock_result.text = "Content"
            mock_result.url = "https://youtube.com/watch?v=test"
            mock_result.start_time_seconds = 100.0
            mock_result.similarity = 0.85
            
            mock_search_response = Mock()
            mock_search_response.results = [mock_result]
            mock_search.return_value = mock_search_response
            
            # Mock OpenAI
            mock_completion = Mock()
            mock_completion.choices = [Mock(message=Mock(content="Answer"))]
            mock_completion.usage = Mock(prompt_tokens=1000, completion_tokens=500)
            
            mock_client = Mock()
            mock_client.chat.completions.create.return_value = mock_completion
            mock_openai.return_value = mock_client
            
            # Make request
            response = client.post(
                "/answer",
                json={"query": "test", "top_k": 10}
            )
            
            assert response.status_code == 200
            
            # Verify correct model was used
            call_args = mock_client.chat.completions.create.call_args
            assert call_args[1]["model"] == "gpt-4o"
            assert call_args[1]["temperature"] == 0.1  # Medical accuracy
            assert call_args[1]["max_tokens"] == 1500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
