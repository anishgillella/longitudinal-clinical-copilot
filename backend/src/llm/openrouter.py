"""
OpenRouter LLM Client

Provides access to various LLMs through OpenRouter's unified API.
Default model: google/gemini-2.5-flash
"""

import httpx
import json
import logging
from typing import Optional, AsyncGenerator

from src.config import get_settings

logger = logging.getLogger(__name__)


class OpenRouterClient:
    """Client for OpenRouter API."""

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

        async with httpx.AsyncClient(timeout=120.0) as client:
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

        async with httpx.AsyncClient(timeout=120.0) as client:
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

    async def health_check(self) -> bool:
        """Check if OpenRouter API is accessible."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/models",
                    headers=self.headers,
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"OpenRouter health check failed: {e}")
            return False
