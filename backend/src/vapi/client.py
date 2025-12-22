import httpx
from typing import Optional
from src.config import get_settings


class VAPIClient:
    """Client for interacting with VAPI API."""

    BASE_URL = "https://api.vapi.ai"

    def __init__(self):
        self.settings = get_settings()
        self.headers = {
            "Authorization": f"Bearer {self.settings.vapi_api_key}",
            "Content-Type": "application/json",
        }

    async def get_call(self, call_id: str) -> dict:
        """Get call details including transcript."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/call/{call_id}",
                headers=self.headers,
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

    async def list_calls(
        self,
        assistant_id: Optional[str] = None,
        limit: int = 100,
    ) -> list[dict]:
        """List calls, optionally filtered by assistant."""
        params = {"limit": limit}
        if assistant_id:
            params["assistantId"] = assistant_id

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/call",
                headers=self.headers,
                params=params,
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

    async def end_call(self, call_id: str) -> dict:
        """End an active call."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/call/{call_id}/stop",
                headers=self.headers,
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

    async def get_assistant(self, assistant_id: str) -> dict:
        """Get assistant details."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/assistant/{assistant_id}",
                headers=self.headers,
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

    async def create_call(
        self,
        assistant_id: str,
        phone_number: str,
        metadata: Optional[dict] = None,
    ) -> dict:
        """
        Create an outbound call.

        Note: This requires a phone number configured in VAPI.
        For web-based calls, use the VAPI Web SDK instead.
        """
        payload = {
            "assistantId": assistant_id,
            "customer": {"number": phone_number},
        }

        if self.settings.vapi_phone_number_id:
            payload["phoneNumberId"] = self.settings.vapi_phone_number_id

        if metadata:
            payload["metadata"] = metadata

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/call/phone",
                headers=self.headers,
                json=payload,
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()
