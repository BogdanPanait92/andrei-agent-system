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
    user_name: str = "Andrei"

    # LLM - Grok (xAI)
    xai_api_key: str = ""
    grok_model: str = "grok-4.3"

    # LLM - Fallbacks
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-sonnet-20241022"
    llm_fallback_order: str = "grok,anthropic,openai"

    # Notion
    notion_api_key: str = ""
    notion_family_db_id: str = ""
    notion_ideas_db_id: str = ""
    notion_content_creation_id: str = ""
    notion_posting_plan_db_id: str = ""
    notion_ajut_cum_pot_db_id: str = ""
    notion_job_db_id: str = ""
    notion_briefings_page_id: str = ""

    # Google
    google_credentials_json: str = ""
    google_calendar_id: str = "primary"
    google_drive_folder_id: str = ""
    google_sheet_ajut_cum_pot_id: str = ""
    google_sheet_ajut_tab: str = "Sheet1"
    google_sheet_editor_pipeline_id: str = ""
    google_sheet_editor_tab: str = "Sheet1"

    # Notifier: telegram | whatsapp | discord
    notifier_provider: Literal["telegram", "whatsapp", "discord"] = "telegram"

    # Discord (Incoming Webhook — outbound notifications)
    discord_webhook_url: str = ""
    discord_webhook_username: str = "Andrei AI"

    # Discord Bot (two-way chat)
    discord_bot_token: str = ""
    discord_allowed_channel_ids: str = ""
    discord_allowed_user_ids: str = ""
    enable_discord_bot: bool = False

    # Discord voice messages (transcription via OpenAI Whisper)
    enable_discord_voice: bool = True
    discord_voice_language: str = "ro"
    discord_voice_model: str = "whisper-1"
    discord_voice_max_duration_seconds: int = 120
    discord_voice_max_bytes: int = 25_000_000

    # Web search (explicit trigger only — e.g. caută: or caută pe net)
    enable_research_mode: bool = True

    enable_web_search: bool = True
    web_search_max_results: int = 5
    web_search_fetch_pages: bool = True
    web_search_max_pages_to_read: int = 3
    web_search_page_char_limit: int = 3500
    web_search_page_max_bytes: int = 500_000
    web_search_fetch_timeout_seconds: int = 15

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
    enable_task_reminder: bool = True
    task_reminder_interval_hours: int = 2
    task_reminder_discord: bool = True
    task_reminder_discord_dm: bool = True
    task_reminder_discord_dm_user_ids: str = ""
    task_reminder_start_hour: int = 8
    task_reminder_end_hour: int = 18
    task_reminder_days: str = "mon,tue,wed,thu,fri,sat"

    # Auto voice-over for Notion ideas missing scripts
    enable_auto_voiceover: bool = True
    auto_voiceover_interval_minutes: int = 60
    auto_voiceover_max_per_run: int = 2
    auto_voiceover_statuses: str = "Draft"
    auto_voiceover_notify_discord: bool = True

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