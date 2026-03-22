from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "stiptrack"
    app_version: str = "0.1.0"
    debug: bool = Field(default=True, validation_alias="APP_DEBUG")
    secret_key: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 30

    api_v1_prefix: str = "/api/v1"
    allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"]
    )
    rate_limit_enabled: bool = True
    rate_limit_storage_uri: str = "redis://localhost:6379/3"
    rate_limit_auth_register: str = "5/minute"
    rate_limit_auth_login: str = "10/minute"
    rate_limit_auth_refresh: str = "20/minute"
    rate_limit_auth_logout: str = "30/minute"
    rate_limit_ai_job_poll: str = "120/minute"
    rate_limit_ai_parse_nizom: str = "10/minute"
    rate_limit_ai_generate_columns: str = "5/minute"
    rate_limit_ai_generate_review: str = "10/minute"
    rate_limit_nizom_upload: str = "10/minute"
    rate_limit_value_upload: str = "30/minute"
    rate_limit_achievement_upload: str = "30/minute"
    rate_limit_application_submit: str = "15/minute"
    rate_limit_winner_announce: str = "5/hour"
    rate_limit_appeal_create: str = "5/hour"
    rate_limit_appeal_upload: str = "10/hour"

    database_url: str = "postgresql+asyncpg://stipuser:stippass@localhost:5432/stipendiya_db"
    database_echo: bool = False

    redis_url: str = "redis://localhost:6379/0"

    minio_endpoint: str = "localhost:9000"
    minio_public_endpoint: str | None = None
    minio_public_path_prefix: str = ""
    minio_public_read_prefixes: list[str] = Field(default_factory=list)
    minio_access_key: str = ""
    minio_secret_key: str = ""
    minio_bucket: str = "stipendiya-files"
    minio_use_ssl: bool = False
    minio_presigned_expiry_seconds: int = 900

    default_llm_provider: str = "claude"
    anthropic_model: str = "claude-sonnet-4-20250514"
    anthropic_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_api_key: str = ""
    gemini_model: str = "gemini-1.5-pro"
    google_api_key: str = ""
    ollama_model: str = "llama3.1"
    ollama_base_url: str = "http://localhost:11434"
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-chat"

    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    mcp_server_port: int = 8001

    email_enabled: bool = False
    frontend_base_url: str | None = None
    mail_username: str = ""
    mail_password: str = ""
    mail_from: str = "noreply@example.com"
    mail_from_name: str = "StipTrack"
    mail_port: int = 1025
    mail_server: str = "localhost"
    mail_starttls: bool = False
    mail_ssl_tls: bool = False
    mail_use_credentials: bool = False
    mail_validate_certs: bool = True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
