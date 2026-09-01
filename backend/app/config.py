"""
WhatsApp Commerce Platform — Configuration
Loads all settings from environment variables via pydantic-settings.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # --- App ---
    APP_NAME: str = "WhatsApp Commerce Platform"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"

    # --- Database ---
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/whatsapp_commerce"
    DATABASE_ECHO: bool = False

    # --- Gemini ---
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # --- WhatsApp Business Cloud API ---
    WA_PHONE_NUMBER_ID: str = ""
    WA_ACCESS_TOKEN: str = ""
    WA_VERIFY_TOKEN: str = "whatsapp-commerce-verify-token"
    WA_APP_SECRET: str = ""
    WA_API_VERSION: str = "v21.0"

    # --- Auth ---
    JWT_SECRET_KEY: str = "jwt-secret-change-me"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 1440  # 24 hours

    # --- Default seller config (used for seeding) ---
    DEFAULT_BUSINESS_NAME: str = "My Store"
    DEFAULT_PRODUCT_CATEGORY: str = "general merchandise"
    DEFAULT_AUTO_APPROVE_LIMIT: float = 25000.0

    model_config = {"env_file": ".env", "extra": "ignore"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
