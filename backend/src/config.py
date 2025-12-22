from pydantic_settings import BaseSettings
from functools import lru_cache
from urllib.parse import quote_plus


class Settings(BaseSettings):
    # Application
    app_name: str = "Longitudinal Clinical Copilot"
    debug: bool = True

    # Server
    backend_port: int = 8000
    frontend_port: int = 3000
    backend_url: str = "http://localhost:8000"
    ngrok_url: str = "https://sustentacular-giada-chunkily.ngrok-free.dev"

    # Database - separate fields for proper URL encoding
    supabase_host: str = "db.bwhvbmlzccmmfnrmctyk.supabase.co"
    supabase_password: str = ""
    supabase_user: str = "postgres"
    supabase_db: str = "postgres"
    supabase_port: int = 5432

    # Legacy - will be overridden by property
    database_url: str = ""

    @property
    def get_database_url(self) -> str:
        """Build database URL with properly encoded password."""
        if self.supabase_password:
            encoded_password = quote_plus(self.supabase_password)
            return f"postgresql+asyncpg://{self.supabase_user}:{encoded_password}@{self.supabase_host}:{self.supabase_port}/{self.supabase_db}"
        return self.database_url or "postgresql+asyncpg://postgres:postgres@localhost:5432/clinical_copilot"

    # VAPI (Phase 2)
    vapi_api_key: str = ""
    vapi_phone_number_id: str = ""
    vapi_assistant_id: str = ""  # Default assistant ID
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
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
