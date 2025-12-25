"""
VAPI API Client

Handles communication with the VAPI API for:
- Managing calls
- Updating assistant configurations
- Syncing webhook URLs automatically
"""

import httpx
import logging
from typing import Optional
from src.config import get_settings

logger = logging.getLogger(__name__)


class VAPIClient:
    """Client for interacting with VAPI API."""

    BASE_URL = "https://api.vapi.ai"

    def __init__(self, use_private_key: bool = False):
        """
        Initialize the VAPI client.

        Args:
            use_private_key: If True, use the private API key (for admin operations).
                           If False, use the public API key (for call operations).
        """
        self.settings = get_settings()
        api_key = self.settings.vapi_private_api_key if use_private_key else self.settings.vapi_api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
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

    async def update_assistant(self, assistant_id: str, updates: dict) -> dict:
        """
        Update assistant configuration.

        Args:
            assistant_id: The assistant ID to update
            updates: Dictionary of fields to update (e.g., {"serverUrl": "..."})

        Returns:
            Updated assistant configuration
        """
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{self.BASE_URL}/assistant/{assistant_id}",
                headers=self.headers,
                json=updates,
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()

    async def sync_webhook_url(self, assistant_id: Optional[str] = None) -> bool:
        """
        Sync the webhook URL for the assistant based on current settings.

        This ensures the VAPI assistant always points to the correct webhook URL
        (ngrok in development, production URL in production).

        Args:
            assistant_id: Optional assistant ID. Uses settings default if not provided.

        Returns:
            True if sync was successful, False otherwise.
        """
        assistant_id = assistant_id or self.settings.vapi_assistant_id
        if not assistant_id:
            logger.warning("Cannot sync webhook URL: No assistant ID configured")
            return False

        webhook_url = f"{self.settings.webhook_base_url}/api/v1/vapi/webhook"

        try:
            # Get current assistant config
            current = await self.get_assistant(assistant_id)
            current_url = current.get("serverUrl", "")

            if current_url == webhook_url:
                logger.info(f"VAPI webhook URL already up to date: {webhook_url}")
                return True

            # Update the webhook URL
            result = await self.update_assistant(assistant_id, {"serverUrl": webhook_url})
            new_url = result.get("serverUrl", "")

            if new_url == webhook_url:
                logger.info(f"VAPI webhook URL updated successfully: {webhook_url}")
                return True
            else:
                logger.error(f"Failed to update VAPI webhook URL. Expected: {webhook_url}, Got: {new_url}")
                return False

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error syncing VAPI webhook URL: {e.response.status_code} - {e.response.text}")
            return False
        except Exception as e:
            logger.error(f"Error syncing VAPI webhook URL: {e}")
            return False


async def sync_vapi_webhook_on_startup():
    """
    Sync VAPI webhook URL on application startup.

    Call this from your FastAPI lifespan or startup event to automatically
    configure VAPI to send webhooks to the correct URL.
    """
    settings = get_settings()

    if not settings.vapi_private_api_key:
        logger.warning(
            "VAPI private API key not configured. "
            "Set VAPI_PRIVATE_API_KEY in .env to enable automatic webhook sync."
        )
        return False

    # Use private key for admin operations
    client = VAPIClient(use_private_key=True)
    success = await client.sync_webhook_url()

    if success:
        logger.info("VAPI webhook URL synced successfully on startup")
    else:
        logger.warning(
            "Failed to sync VAPI webhook URL on startup. "
            "Webhooks may not work. Check your VAPI_PRIVATE_API_KEY and NGROK_URL settings."
        )

    return success
