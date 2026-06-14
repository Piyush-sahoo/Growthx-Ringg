"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings. Values come from environment / .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_name: str = "growthx-ringg-backend"
    environment: str = "development"

    # Ringg AI — https://docs.ringg.ai  (auth: X-API-KEY header)
    ringg_api_key: str = ""
    ringg_base_url: str = "https://prod-api.ringg.ai/ca/api/v0"
    # agent_id of the assistant configured for outbound calls (GET /agent/all).
    ringg_assistant_id: str = ""
    # Caller ID — preferred over a raw number (GET /workspace/numbers).
    ringg_from_number_id: str = ""
    # Shared secret used to verify inbound Ringg webhook calls.
    ringg_webhook_secret: str = ""

    # CORS — comma-separated list of allowed origins for the frontend.
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor."""
    return Settings()
