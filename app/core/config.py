from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "FinSync AI Backend"
    ENV: str = "dev"
    DATABASE_URL: str = "sqlite:///./finsync.db"  # later: postgres://...

    class Config:
        env_file = ".env"

settings = Settings()
