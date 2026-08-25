import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    BOT_TOKEN: str
    ADMIN_IDS: list[int] = []
    DB_URL: str
    BANNER_MAIN: str = "https://www.boxexchanger.net/_nuxt/telegram-bot.CXxjD6Gh.jpg"
    BANNER_EXCHANGE: str = "https://www.boxexchanger.net/_nuxt/payment-gateway.D1ePChF0.jpg"
    BANNER_PROFILE: str = "https://www.boxexchanger.net/_nuxt/faq.C0JBDugW.jpg"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

config = Settings()