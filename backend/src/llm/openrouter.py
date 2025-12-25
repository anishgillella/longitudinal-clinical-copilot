"""
OpenRouter LLM Client

Provides access to various LLMs through OpenRouter's unified API.
Default model: google/gemini-2.5-flash

Supports Pydantic model validation for structured outputs.

Optimized with connection pooling for faster parallel requests.
"""

import httpx
import json
import logging
from typing import Optional, AsyncGenerator, TypeVar, Type

from pydantic import BaseModel, ValidationError

from src.config import get_settings

logger = logging.getLogger(__name__)

# Type variable for generic Pydantic model support
T = TypeVar('T', bound=BaseModel)

# Shared HTTP client for connection pooling across all instances
# This dramatically improves performance for parallel LLM calls
_shared_client: Optional[httpx.AsyncClient] = None


async def get_shared_client() -> httpx.AsyncClient:
    """Get or create the shared HTTP client with connection pooling."""
    global _shared_client
    if _shared_client is None or _shared_client.is_closed:
        _shared_client = httpx.AsyncClient(
            timeout=httpx.Timeout(120.0, connect=10.0),
            limits=httpx.Limits(
                max_keepalive_connections=10,
                max_connections=20,
                keepalive_expiry=30.0,
            ),
            http2=True,  # HTTP/2 for multiplexing
        )
    return _shared_client


async def close_shared_client():
    """Close the shared client (call on app shutdown)."""
    global _shared_client
    if _shared_client is not None and not _shared_client.is_closed:
        await _shared_client.aclose()
        _shared_client = None


class OpenRouterClient:
    """Client for OpenRouter API with connection pooling."""

    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(self, model: Optional[str] = None):
        self.settings = get_settings()
        self.model = model or self.settings.openrouter_model
        self.headers = {
            "Authorization": f"Bearer {self.settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://clinical-copilot.local",
            "X-Title": "Longitudinal Clinical Copilot",
        }

    async def complete(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2000,
        response_format: Optional[dict] = None,
    ) -> dict:
        """
        Generate a completion from OpenRouter.

        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Override default model
            temperature: Sampling temperature (lower = more deterministic)
            max_tokens: Maximum tokens in response
            response_format: Optional format specification (e.g., {"type": "json_object"})

        Returns:
            Full API response dict
        """
        payload = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if response_format:
            payload["response_format"] = response_format

        # Use shared client for connection pooling
        client = await get_shared_client()
        response = await client.post(
            f"{self.BASE_URL}/chat/completions",
            headers=self.headers,
            json=payload,
        )
        response.raise_for_status()
        return response.json()

    async def complete_text(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 2000,
    ) -> str:
        """
        Generate a completion and return just the text content.

        Returns:
            The assistant's response text
        """
        result = await self.complete(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return result["choices"][0]["message"]["content"]

    async def complete_json(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4000,
    ) -> dict:
        """
        Generate a JSON-structured completion.

        The last message should ask for JSON output.
        Uses lower temperature for more consistent structure.

        Returns:
            Parsed JSON dict from the response
        """
        # Add JSON instruction if not present
        enhanced_messages = messages.copy()
        last_msg = enhanced_messages[-1]["content"]
        if "json" not in last_msg.lower():
            enhanced_messages[-1]["content"] = last_msg + "\n\nRespond with valid JSON only."

        result = await self.complete(
            messages=enhanced_messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )

        content = result["choices"][0]["message"]["content"]

        # Parse JSON, handling potential markdown code blocks
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]

        return json.loads(content.strip())

    async def stream(
        self,
        messages: list[dict],
        model: Optional[str] = None,
        temperature: float = 0.3,
    ) -> AsyncGenerator[str, None]:
        """
        Stream a completion from OpenRouter.

        Yields:
            Text chunks as they arrive
        """
        payload = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }

        # Use shared client for connection pooling
        client = await get_shared_client()
        async with client.stream(
            "POST",
            f"{self.BASE_URL}/chat/completions",
            headers=self.headers,
            json=payload,
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        if "content" in delta:
                            yield delta["content"]
                    except json.JSONDecodeError:
                        continue

    async def analyze_transcript(
        self,
        transcript: str,
        system_prompt: str,
        user_prompt: str,
    ) -> dict:
        """
        Convenience method for analyzing session transcripts.

        Args:
            transcript: The conversation transcript
            system_prompt: System instructions for analysis
            user_prompt: Specific analysis request

        Returns:
            Parsed JSON analysis result
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{user_prompt}\n\nTRANSCRIPT:\n{transcript}"},
        ]
        return await self.complete_json(messages)

    async def complete_structured(
        self,
        messages: list[dict],
        response_model: Type[T],
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 4000,
        retry_on_validation_error: bool = True,
    ) -> T:
        """
        Generate a completion and validate against a Pydantic model.

        This method ensures type-safe, validated outputs from LLM calls.
        If validation fails and retry is enabled, it will attempt once more
        with the validation errors included in the prompt.

        Args:
            messages: List of message dicts with 'role' and 'content'
            response_model: Pydantic model class to validate against
            model: Override default model
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            retry_on_validation_error: Whether to retry with error context

        Returns:
            Validated Pydantic model instance

        Raises:
            ValidationError: If response doesn't match model after retries
        """
        # Get JSON schema from Pydantic model
        schema = response_model.model_json_schema()

        # Add schema hint to messages
        enhanced_messages = messages.copy()
        schema_hint = f"\n\nRespond with JSON matching this schema:\n{json.dumps(schema, indent=2)}"
        enhanced_messages[-1]["content"] = enhanced_messages[-1]["content"] + schema_hint

        try:
            # Get JSON response
            result = await self.complete_json(
                messages=enhanced_messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            # Validate with Pydantic
            return response_model.model_validate(result)

        except ValidationError as e:
            if not retry_on_validation_error:
                raise

            logger.warning(f"Validation error, retrying with context: {e}")

            # Retry with validation errors in context
            retry_messages = enhanced_messages.copy()
            retry_messages.append({
                "role": "assistant",
                "content": json.dumps(result) if 'result' in dir() else "{}"
            })
            retry_messages.append({
                "role": "user",
                "content": f"The previous response had validation errors:\n{str(e)}\n\nPlease fix the response to match the schema exactly."
            })

            retry_result = await self.complete_json(
                messages=retry_messages,
                model=model,
                temperature=temperature * 0.5,  # Lower temperature for retry
                max_tokens=max_tokens,
            )

            return response_model.model_validate(retry_result)

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            raise ValueError(f"Failed to parse LLM response as JSON: {e}")

    async def extract_signals_structured(
        self,
        transcript: str,
        session_type: str,
        domains_text: str,
    ):
        """
        Extract signals with Pydantic validation.

        Returns:
            SignalExtractionResult validated model
        """
        from src.schemas.llm_outputs import SignalExtractionResult
        from src.llm.prompts import SIGNAL_EXTRACTION_SYSTEM, SIGNAL_EXTRACTION_USER

        user_prompt = SIGNAL_EXTRACTION_USER.format(
            session_type=session_type,
            domains_text=domains_text,
            transcript=transcript,
        )

        messages = [
            {"role": "system", "content": SIGNAL_EXTRACTION_SYSTEM},
            {"role": "user", "content": user_prompt},
        ]

        return await self.complete_structured(
            messages=messages,
            response_model=SignalExtractionResult,
            temperature=0.2,
            max_tokens=6000,
        )

    async def generate_hypotheses_structured(
        self,
        domain_scores_json: str,
        signal_count: int,
        signals_summary: str,
        session_summary: str,
    ):
        """
        Generate hypotheses with Pydantic validation.

        Returns:
            HypothesisGenerationResult validated model
        """
        from src.schemas.llm_outputs import HypothesisGenerationResult
        from src.llm.prompts import HYPOTHESIS_GENERATION_SYSTEM, HYPOTHESIS_GENERATION_USER

        user_prompt = HYPOTHESIS_GENERATION_USER.format(
            domain_scores_json=domain_scores_json,
            signal_count=signal_count,
            signals_summary=signals_summary,
            session_summary=session_summary,
        )

        messages = [
            {"role": "system", "content": HYPOTHESIS_GENERATION_SYSTEM},
            {"role": "user", "content": user_prompt},
        ]

        return await self.complete_structured(
            messages=messages,
            response_model=HypothesisGenerationResult,
            temperature=0.3,
            max_tokens=6000,
        )

    async def score_domains_structured(
        self,
        signals_json: str,
        domains_text: str,
    ):
        """
        Score domains with Pydantic validation.

        Returns:
            DomainScoringResult validated model
        """
        from src.schemas.llm_outputs import DomainScoringResult
        from src.llm.prompts import DOMAIN_SCORING_SYSTEM, DOMAIN_SCORING_USER

        user_prompt = DOMAIN_SCORING_USER.format(
            signals_json=signals_json,
            domains_text=domains_text,
        )

        messages = [
            {"role": "system", "content": DOMAIN_SCORING_SYSTEM},
            {"role": "user", "content": user_prompt},
        ]

        return await self.complete_structured(
            messages=messages,
            response_model=DomainScoringResult,
            temperature=0.2,
            max_tokens=4000,
        )

    async def health_check(self) -> bool:
        """Check if OpenRouter API is accessible."""
        try:
            client = await get_shared_client()
            response = await client.get(
                f"{self.BASE_URL}/models",
                headers=self.headers,
            )
            return response.status_code == 200
        except Exception as e:
            logger.error(f"OpenRouter health check failed: {e}")
            return False
