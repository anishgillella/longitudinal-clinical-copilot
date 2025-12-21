from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Application
    app_name: str = "Longitudinal Clinical Copilot"
    debug: bool = True

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/clinical_copilot"

    # VAPI (Phase 2)
    vapi_api_key: str = ""
    vapi_phone_number_id: str = ""
    vapi_assistant_id: str = ""  # Default assistant ID
    vapi_webhook_secret: str = ""  # Optional webhook verification

    # OpenRouter (Phase 3)
    openrouter_api_key: str = ""
    openrouter_model: str = "google/gemini-2.5-flash"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
