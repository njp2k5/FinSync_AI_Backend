from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # -------------------------
    # App core settings
    # -------------------------
    app_name: str = "FinSync AI Backend"
    env: str = "dev"

    # -------------------------
    # Database
    # -------------------------
    database_url: str = "sqlite:///./finsync.db"

    # -------------------------
    # JWT / Auth settings
    # -------------------------
    secret_key: str = "CHANGE_ME_IN_PROD"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # -------------------------
    # External integrations
    # -------------------------
    openrouter_api_key: Optional[str] = None
    google_model: Optional[str] = None

    # -------------------------
    # Email / SMTP
    # -------------------------
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_pass: Optional[str] = None
    sender_email: Optional[str] = None

    # -------------------------
    # Pydantic v2 config
    # -------------------------
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="forbid"
    )


# Singleton
settings = Settings()
