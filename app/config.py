"""
config.py — Central Configuration
==================================
This file reads settings from environment variables (your .env file or Railway's
dashboard). Every setting has a sensible default so the app can start locally
without configuring anything.

WHY A SEPARATE FILE?
    Instead of scattering os.getenv() calls throughout the codebase, we keep
    all configuration in one place. If you need to change a default or add a
    new setting, you only touch this file.

HOW IT WORKS:
    Pydantic's BaseSettings automatically reads from environment variables.
    Variable names are case-insensitive (REDIS_URL and redis_url both work).
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """
    All application settings. Each field maps to an environment variable.
    For example, the field `redis_url` reads from the env var REDIS_URL.
    """

    # ---- Project Metadata (shown in /docs) ----
    app_name: str = "UK Property Data API"
    app_version: str = "1.0.0"
    app_description: str = (
        "Production API for UK sold prices, rental yields, and stamp duty. "
        "Paid via x402 protocol. Designed for AI agent consumption."
    )

    # ---- Redis ----
    # Used for caching Land Registry responses and for rate limiting.
    # Railway injects this automatically when you add a Redis plugin.
    # Set to empty string to run without Redis (caching will be skipped).
    redis_url: str = ""

    # ---- x402 Payment Protocol ----
    # The facilitator is a third-party service that verifies payments.
    x402_facilitator_url: str = "https://x402.org/facilitator"

    # Your wallet address — where payments are sent.
    payment_wallet_address: str = ""

    # Cost per API call in USD.
    price_per_request: str = "0.001"

    # ---- Rate Limiting ----
    # Max requests per wallet address per minute.
    rate_limit_per_minute: int = 30

    # ---- Caching ----
    # Time-to-live for cached postcode results, in seconds.
    # 3600 = 1 hour. Land Registry data doesn't change often.
    cache_ttl_seconds: int = 3600

    # ---- EPC API ----
    # Optional API key for the EPC register. If empty, returns estimated averages.
    epc_api_key: str = ""

    # ---- Logging ----
    log_level: str = "INFO"

    # ---- Server ----
    # Railway sets PORT automatically; we default to 8000 for local dev.
    port: int = 8000

    class Config:
        # Tell Pydantic to also look in a .env file (for local development).
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """
    Returns a cached Settings instance. The @lru_cache decorator ensures we
    only read environment variables once, not on every request.

    Usage in other files:
        from app.config import get_settings
        settings = get_settings()
        print(settings.redis_url)
    """
    return Settings()
