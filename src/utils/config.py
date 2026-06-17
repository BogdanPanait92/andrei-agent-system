"""Application configuration via environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application
    app_env: Literal["development", "production", "test"] = "development"
    log_level: str = "INFO"
    timezone: str = "Europe/Bucharest"
    andrei_name: str = "Andrei"

    # LLM - Grok (xAI)
    xai_api_key: str = ""
    grok_model: str = "grok-2-latest"

    # LLM - Fallbacks
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-sonnet-20241022"
    llm_fallback_order: str = "grok,anthropic,openai"

    # Notion
    notion_api_key: str = ""
    notion_tasks_db_id: str = ""
    notion_ideas_db_id: str = ""
    notion_posting_plan_db_id: str = ""
    notion_ajut_cum_pot_db_id: str = ""
    notion_journal_db_id: str = ""
    notion_briefings_page_id: str = ""

    # Google
    google_credentials_json: str = ""
    google_calendar_id: str = "primary"
    google_drive_folder_id: str = ""

    # Notifier: telegram | whatsapp
    notifier_provider: Literal["telegram", "whatsapp"] = "telegram"

    # Telegram
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # WhatsApp Business Cloud API (Meta)
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""
    whatsapp_recipient: str = ""  # E.164: 40722123456
    whatsapp_api_version: str = "v21.0"
    whatsapp_template_language: str = "ro"
    whatsapp_template_daily: str = ""
    whatsapp_template_weekly: str = ""
    whatsapp_template_general: str = ""

    # Supabase
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_service_key: str = ""

    # Pinecone
    pinecone_api_key: str = ""
    pinecone_index_name: str = "andreia-memory"
    pinecone_environment: str = "us-east-1"

    memory_provider: Literal["supabase", "pinecone"] = "supabase"

    # Railway / Server
    port: int = 8000
    railway_environment: str = "development"

    # Scheduler
    daily_briefing_hour: int = 7
    daily_briefing_minute: int = 0
    weekly_review_day: str = "sunday"
    weekly_review_hour: int = 20
    enable_scheduler: bool = True

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def llm_providers(self) -> list[str]:
        return [p.strip() for p in self.llm_fallback_order.split(",") if p.strip()]

    def validate_required(self, *keys: str) -> None:
        missing = [k for k in keys if not getattr(self, k, None)]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()