from functools import lru_cache

from pydantic import AnyHttpUrl, Field, PositiveInt, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str
    log_level: str
    webhook_path: str

    ai_pipeline_url: AnyHttpUrl
    ai_pipeline_timeout_seconds: PositiveInt

    supabase_url: AnyHttpUrl
    supabase_service_role_key: str = Field(repr=False)
    supabase_table: str

    cloudinary_api_secret: str = Field(repr=False)
    cloudinary_signature_required: bool
    cloudinary_signature_tolerance_seconds: PositiveInt

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
