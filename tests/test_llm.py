"""
Tests for LLM Client

Tests the OpenRouter client with mocked HTTP responses.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import json

from src.llm.openrouter import OpenRouterClient


class TestOpenRouterClient:
    """Tests for OpenRouter LLM client."""

    def test_client_initialization(self):
        """Test client initializes with correct defaults."""
        client = OpenRouterClient()
        assert client.model == "google/gemini-2.5-flash"
        assert client.BASE_URL == "https://openrouter.ai/api/v1"

    def test_client_custom_model(self):
        """Test client can use custom model."""
        client = OpenRouterClient(model="anthropic/claude-3.5-sonnet")
        assert client.model == "anthropic/claude-3.5-sonnet"

    @pytest.mark.asyncio
    async def test_complete_json_success(self):
        """Test successful JSON completion."""
        client = OpenRouterClient()

        mock_response = {
            "choices": [
                {
                    "message": {
                        "content": '{"test": "value", "count": 42}'
                    }
                }
            ]
        }

        with patch.object(client, 'complete', new_callable=AsyncMock) as mock_complete:
            mock_complete.return_value = mock_response

            result = await client.complete_json(
                messages=[{"role": "user", "content": "test"}]
            )

            assert result == {"test": "value", "count": 42}
            mock_complete.assert_called_once()

    @pytest.mark.asyncio
    async def test_complete_json_with_code_block(self):
        """Test parsing JSON from markdown code block."""
        client = OpenRouterClient()

        mock_response = {
            "choices": [
                {
                    "message": {
                        "content": '```json\n{"test": "value"}\n```'
                    }
                }
            ]
        }

        with patch.object(client, 'complete', new_callable=AsyncMock) as mock_complete:
            mock_complete.return_value = mock_response

            result = await client.complete_json(
                messages=[{"role": "user", "content": "test"}]
            )

            assert result == {"test": "value"}

    @pytest.mark.asyncio
    async def test_complete_json_invalid_json_raises(self):
        """Test handling invalid JSON response raises an error."""
        client = OpenRouterClient()

        mock_response = {
            "choices": [
                {
                    "message": {
                        "content": "This is not valid JSON"
                    }
                }
            ]
        }

        with patch.object(client, 'complete', new_callable=AsyncMock) as mock_complete:
            mock_complete.return_value = mock_response

            # The client raises JSONDecodeError on invalid JSON
            with pytest.raises(json.JSONDecodeError):
                await client.complete_json(
                    messages=[{"role": "user", "content": "test"}]
                )

    @pytest.mark.asyncio
    async def test_analyze_transcript(self):
        """Test transcript analysis convenience method."""
        client = OpenRouterClient()

        mock_response = {"signals": [], "summary": "test"}

        with patch.object(client, 'complete_json', new_callable=AsyncMock) as mock_complete:
            mock_complete.return_value = mock_response

            result = await client.analyze_transcript(
                transcript="Patient: Hello",
                system_prompt="You are an analyst",
                user_prompt="Analyze this transcript",
            )

            assert result == {"signals": [], "summary": "test"}
            # Verify messages were constructed correctly
            call_args = mock_complete.call_args[0][0]  # First positional arg (messages)
            assert len(call_args) == 2
            assert call_args[0]["role"] == "system"
            assert call_args[1]["role"] == "user"
            assert "Patient: Hello" in call_args[1]["content"]

    @pytest.mark.asyncio
    async def test_complete_text(self):
        """Test text completion method."""
        client = OpenRouterClient()

        mock_response = {
            "choices": [
                {
                    "message": {
                        "content": "This is a text response"
                    }
                }
            ]
        }

        with patch.object(client, 'complete', new_callable=AsyncMock) as mock_complete:
            mock_complete.return_value = mock_response

            result = await client.complete_text(
                messages=[{"role": "user", "content": "test"}]
            )

            assert result == "This is a text response"


class TestPromptTemplates:
    """Tests for prompt templates."""

    def test_signal_extraction_prompts_exist(self):
        """Test signal extraction prompts are defined."""
        from src.llm.prompts import SIGNAL_EXTRACTION_SYSTEM, SIGNAL_EXTRACTION_USER

        assert SIGNAL_EXTRACTION_SYSTEM
        assert SIGNAL_EXTRACTION_USER
        assert "{transcript}" in SIGNAL_EXTRACTION_USER

    def test_session_summary_prompts_exist(self):
        """Test session summary prompts are defined."""
        from src.llm.prompts import SESSION_SUMMARY_SYSTEM, SESSION_SUMMARY_USER

        assert SESSION_SUMMARY_SYSTEM
        assert SESSION_SUMMARY_USER
        assert "{transcript}" in SESSION_SUMMARY_USER

    def test_domain_scoring_prompts_exist(self):
        """Test domain scoring prompts are defined."""
        from src.llm.prompts import DOMAIN_SCORING_SYSTEM, DOMAIN_SCORING_USER

        assert DOMAIN_SCORING_SYSTEM
        assert DOMAIN_SCORING_USER
        assert "{signals_json}" in DOMAIN_SCORING_USER

    def test_hypothesis_generation_prompts_exist(self):
        """Test hypothesis generation prompts are defined."""
        from src.llm.prompts import HYPOTHESIS_GENERATION_SYSTEM, HYPOTHESIS_GENERATION_USER

        assert HYPOTHESIS_GENERATION_SYSTEM
        assert HYPOTHESIS_GENERATION_USER
        assert "{domain_scores_json}" in HYPOTHESIS_GENERATION_USER

    def test_concern_detection_prompts_exist(self):
        """Test concern detection prompts are defined."""
        from src.llm.prompts import CONCERN_DETECTION_SYSTEM, CONCERN_DETECTION_USER

        assert CONCERN_DETECTION_SYSTEM
        assert CONCERN_DETECTION_USER
        assert "{transcript}" in CONCERN_DETECTION_USER

    def test_prompts_emphasize_hypotheses_not_diagnoses(self):
        """Test that prompts emphasize hypotheses, not diagnoses."""
        from src.llm.prompts import HYPOTHESIS_GENERATION_SYSTEM

        # The prompt should emphasize these are hypotheses for clinician review
        lower_prompt = HYPOTHESIS_GENERATION_SYSTEM.lower()
        assert "hypothesis" in lower_prompt or "hypotheses" in lower_prompt
        # Should mention uncertainty
        assert "uncertainty" in lower_prompt or "uncertain" in lower_prompt
