from functools import lru_cache

from pydantic import AnyHttpUrl, Field, PositiveInt, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "gungfi-webhook-be"
    log_level: str = "INFO"
    webhook_path: str = "/cloudinary-trigger"

    ai_pipeline_url: AnyHttpUrl = "http://be-aipipeline-jeki.indonesiacentral.azurecontainer.io:8000"
    ai_pipeline_timeout_seconds: PositiveInt = 60

    supabase_url: AnyHttpUrl | None = None
    supabase_service_role_key: str | None = Field(default=None, repr=False)
    supabase_table: str = "reports"

    cloudinary_api_secret: str | None = Field(default=None, repr=False)
    cloudinary_signature_required: bool = True
    cloudinary_signature_tolerance_seconds: PositiveInt = 7200

    @field_validator("webhook_path")
    @classmethod
    def normalize_webhook_path(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("WEBHOOK_PATH cannot be empty")
        return value if value.startswith("/") else f"/{value}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
