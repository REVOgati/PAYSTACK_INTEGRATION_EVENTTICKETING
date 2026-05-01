from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):

    # ── App ──────────────────────────────────────────────────────
    APP_ENV: str = "development"
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # ── Database ─────────────────────────────────────────────────
    DATABASE_URL: str

    # ── Paystack ─────────────────────────────────────────────────
    PAYSTACK_SECRET_KEY: str
    PAYSTACK_PUBLIC_KEY: str
    PAYSTACK_BASE_URL: str = "https://api.paystack.co"

    # ── URLs ─────────────────────────────────────────────────────
    CALLBACK_URL: str
    WEBHOOK_URL: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()