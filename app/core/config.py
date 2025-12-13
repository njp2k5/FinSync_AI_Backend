# app/core/config.py
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # App core settings
    APP_NAME: str = "FinSync AI Backend"
    ENV: str = "dev"

    # Database
    DATABASE_URL: str = "sqlite:///./finsync.db"

    # JWT / Auth settings  ✅ REQUIRED
    SECRET_KEY: str = "CHANGE_ME_IN_PROD"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # External integrations
    GOOGLE_API_KEY: Optional[str] = None
    GOOGLE_MODEL: Optional[str] = None

    # Email / SMTP
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASS: Optional[str] = None
    SENDER_EMAIL: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# singleton settings object
settings = Settings()
