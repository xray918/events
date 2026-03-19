"""Application configuration"""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "Events"
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "change-me-in-production"

    # Server
    port: int = 8082

    # API
    api_v1_prefix: str = "/api/v1"

    # Database (shared with ClawdChat)
    database_url: str = "postgresql+asyncpg://clawdchat:clawdchat123@localhost:5432/clawdchat"

    # Redis
    redis_url: str = "redis://localhost:6379/1"

    # CORS
    cors_origins: str = "http://localhost:3032"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]

    # Google OAuth (shared with ClawdChat)
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8082/api/v1/auth/google/callback"

    # Frontend URL
    frontend_url: str = "http://localhost:3032"

    # ClawdChat API integration
    clawdchat_api_base: str = "https://clawdchat.ai/api/v1"
    events_bot_api_key: str = ""

    # Agent API Key prefix (must match ClawdChat)
    api_key_prefix: str = "clawdchat_"

    # Alibaba Cloud SMS
    alibaba_cloud_access_key_id: str = ""
    alibaba_cloud_access_key_secret: str = ""
    sms_sign_name: str = "虾聊"
    sms_template_code: str = ""
    sms_blast_template_code: str = ""
    sms_winner_template_code: str = ""

    # Image upload (Aliyun OSS)
    image_max_size_mb: int = 5
    oss_endpoint: str = ""
    oss_bucket_name: str = ""
    oss_prefix: str = "events/"

    # OpenRouter LLM (for AI description generation)
    openrouter_api_base: str = "https://openrouter.ai/api/v1"
    openrouter_api_key: str = ""
    openrouter_model: str = "google/gemini-3-flash-preview"

    # Admin
    admin_username: str = ""
    admin_password: str = ""

    # Rate limiting
    rate_limit_per_minute: int = 100


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
