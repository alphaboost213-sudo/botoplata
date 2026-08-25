import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    BOT_TOKEN: str
    ADMIN_IDS: list[int] = []
    WORKER_IDS: list[int] = []
    DB_URL: str = "sqlite+aiosqlite:///exchange.db"
    TRADERCAB_MKEY: str
    WEBHOOK_SECRET: str = ""
    RAILWAY_PUBLIC_DOMAIN: str = ""
    PORT: int = 8000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

config = Settings()

if config.RAILWAY_PUBLIC_DOMAIN:
    WEBHOOK_HOST = f"https://{config.RAILWAY_PUBLIC_DOMAIN}"
    CALLBACK_URL = f"https://{config.RAILWAY_PUBLIC_DOMAIN}/tradercab/callback"
else:
    WEBHOOK_HOST = os.environ.get("WEBHOOK_HOST", "")
    CALLBACK_URL = os.environ.get("CALLBACK_URL", "")
