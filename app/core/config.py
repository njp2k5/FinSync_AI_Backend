# app/core/config.py
# app/core/config.py
from typing import Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # App core settings
    APP_NAME: str = "FinSync AI Backend"
    ENV: str = "dev"
    DATABASE_URL: str = "sqlite:///./finsync.db"

    # External integrations (declare all env variables you use)
    GOOGLE_API_KEY: Optional[str] = None
    GOOGLE_MODEL: Optional[str] = None

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
