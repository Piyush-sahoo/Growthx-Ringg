"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings. Values come from environment / .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    app_name: str = "growthx-ringg-backend"
    environment: str = "development"

    # Persistence — MongoDB Atlas. If unset, an in-memory store is used (dev/tests).
    mongodb_uri: str = ""
    mongodb_db: str = "flowforge"

    # Ringg AI — https://docs.ringg.ai  (auth: X-API-KEY header)
    ringg_api_key: str = ""
    ringg_base_url: str = "https://prod-api.ringg.ai/ca/api/v0"
    # agent_id of the assistant configured for outbound calls (GET /agent/all).
    ringg_assistant_id: str = ""
    # Caller ID — preferred over a raw number (GET /workspace/numbers).
    ringg_from_number_id: str = ""
    # Shared secret used to verify inbound Ringg webhook calls.
    ringg_webhook_secret: str = ""

    # Deploy (S4): where Ringg posts webhooks, and defaults for created agents.
    webhook_callback_url: str = "https://growthx-ringg-backend.onrender.com/webhooks/ringg"
    agent_primary_language: str = "en-IN"
    agent_secondary_language: str = "hi-IN"
    agent_voice_id: str = ""  # if empty, deploy resolves the first voice for the language

    # Gemini (google-genai) — used for the brainstorm/generation + branch fallback.
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    # Resend — email tool (checkout link, forwardable summary).
    resend_api_key: str = ""
    resend_from: str = "FlowForge <onboarding@resend.dev>"

    # Twilio — WhatsApp tool (link delivery via the sandbox).
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_whatsapp_from: str = ""  # e.g. "whatsapp:+14155238886"

    # Telegram — Bot API channel (checkout link / forwardable summary to the user).
    # Token from @BotFather; chat id is the user's or a group's chat id.
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # Slack — incoming webhook (internal escalation: stuck walls, urgent flags).
    slack_webhook_url: str = ""

    # CORS — comma-separated list of allowed origins for the frontend.
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor."""
    return Settings()
