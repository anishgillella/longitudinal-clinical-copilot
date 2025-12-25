from pydantic_settings import BaseSettings
from pydantic import model_validator
from functools import lru_cache
from urllib.parse import quote_plus
from pathlib import Path
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

# Always use the root .env file (belo/.env)
# This ensures consistent configuration across backend and frontend
ROOT_ENV_FILE = Path(__file__).parent.parent.parent / ".env"  # backend/src -> backend -> belo/.env

# Load environment variables from root .env file
if ROOT_ENV_FILE.exists():
    load_dotenv(ROOT_ENV_FILE, override=True)
    logger.info(f"Loaded environment from: {ROOT_ENV_FILE}")
else:
    logger.warning(f"Environment file not found: {ROOT_ENV_FILE}")


class Settings(BaseSettings):
    # Application
    app_name: str = "Longitudinal Clinical Copilot"
    debug: bool = True

    # Server
    backend_port: int = 8000
    frontend_port: int = 3000
    backend_url: str = "http://localhost:8000"
    ngrok_url: str = "https://sustentacular-giada-chunkily.ngrok-free.dev"

    # Database - Supabase ONLY (no local fallback)
    supabase_host: str = ""
    supabase_password: str = ""
    supabase_user: str = "postgres"
    supabase_db: str = "postgres"
    supabase_port: int = 5432

    @model_validator(mode="after")
    def validate_supabase_credentials(self):
        """Ensure Supabase credentials are set - no local database fallback."""
        if not self.supabase_host:
            raise ValueError(
                "SUPABASE_HOST is required. "
                f"Please set it in {ROOT_ENV_FILE}"
            )
        if not self.supabase_password:
            raise ValueError(
                "SUPABASE_PASSWORD is required. "
                f"Please set it in {ROOT_ENV_FILE}"
            )
        return self

    @property
    def get_database_url(self) -> str:
        """Build Supabase database URL with properly encoded password."""
        encoded_password = quote_plus(self.supabase_password)
        return f"postgresql+asyncpg://{self.supabase_user}:{encoded_password}@{self.supabase_host}:{self.supabase_port}/{self.supabase_db}"

    # VAPI (Phase 2)
    vapi_api_key: str = ""
    vapi_private_api_key: str = ""  # Private key for API calls (updating assistant, etc.)
    vapi_phone_number_id: str = ""
    vapi_assistant_id: str = "fdfb1cc6-ba4d-4a3e-a938-f6e3963a8bb9"  # Default assistant ID
    vapi_webhook_secret: str = ""  # Optional webhook verification

    # OpenRouter (Phase 3)
    openrouter_api_key: str = ""
    openrouter_model: str = "google/gemini-2.5-flash"

    @property
    def webhook_base_url(self) -> str:
        """Get the base URL for webhooks (ngrok in dev, production URL in prod)."""
        if self.debug and self.ngrok_url:
            return self.ngrok_url
        return self.backend_url

    class Config:
        # Always use root .env file
        env_file = str(ROOT_ENV_FILE)
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
