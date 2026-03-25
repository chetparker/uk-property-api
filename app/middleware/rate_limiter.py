"""
rate_limiter.py — Per-Wallet Rate Limiting
============================================
Limits how many requests a single wallet address can make per minute.
Uses Redis to track request counts with auto-expiring keys.

WHY RATE LIMIT?
    Without limits, one user (or a misbehaving bot) could:
    - Overwhelm the Land Registry API (they might block our IP).
    - Consume all your server resources.
    - Run up huge payment processing costs.

HOW IT WORKS (Sliding Window Counter):
    1. Each wallet gets a Redis key like "ratelimit:0xABC123:1710864000"
       (the number is the current minute, as a Unix timestamp).
    2. Each request increments the counter.
    3. If the counter exceeds the limit, we reject with HTTP 429.
    4. The key auto-expires after 60 seconds (so old counts disappear).

EXAMPLE:
    If RATE_LIMIT_PER_MINUTE=30, wallet 0xABC can make 30 calls per minute.
    On the 31st call, they get back:
        HTTP 429 Too Many Requests
        {"error": "rate_limited", "detail": "Limit: 30 requests/minute"}
"""

import time
import logging
from typing import Optional

from fastapi import Request, HTTPException

from app.config import get_settings
from app.middleware.cache import get_redis

logger = logging.getLogger(__name__)


async def check_rate_limit(wallet_address: str) -> None:
    """
    Check and increment the rate limit counter for a wallet address.

    Args:
        wallet_address: The wallet making the request (from x402 header).

    Raises:
        HTTPException(429): If the wallet has exceeded its rate limit.
    """
    redis_client = get_redis()
    settings = get_settings()

    # If Redis is not available, skip rate limiting (fail-open).
    # This means the API works even if Redis is down, but without protection.
    if redis_client is None:
        logger.debug("Rate limiting skipped — Redis not available")
        return

    # Build a key that includes the current minute.
    # This creates a new counter every minute automatically.
    current_minute = int(time.time() // 60)
    key = f"ratelimit:{wallet_address}:{current_minute}"

    try:
        # INCR atomically increments and returns the new count.
        # If the key doesn't exist, Redis creates it with value 1.
        count = await redis_client.incr(key)

        # On the first request of a new minute, set the key to expire
        # after 120 seconds (2 minutes, with some buffer).
        if count == 1:
            await redis_client.expire(key, 120)

        if count > settings.rate_limit_per_minute:
            logger.warning(
                f"Rate limit exceeded for wallet {wallet_address}: "
                f"{count}/{settings.rate_limit_per_minute} requests this minute"
            )
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "rate_limited",
                    "detail": (
                        f"Rate limit exceeded. Maximum {settings.rate_limit_per_minute} "
                        f"requests per minute. Try again in a few seconds."
                    ),
                    "limit": settings.rate_limit_per_minute,
                    "current": count,
                },
            )

        logger.debug(
            f"Rate limit OK for {wallet_address}: "
            f"{count}/{settings.rate_limit_per_minute}"
        )

    except HTTPException:
        # Re-raise our 429 — don't swallow it.
        raise
    except Exception as e:
        # If Redis fails, let the request through (fail-open).
        logger.warning(f"Rate limit check failed: {e}")


def extract_wallet_from_request(request: Request) -> Optional[str]:
    """
    Extract the wallet address from the x402 payment header.

    The x402 protocol sends payment proof in the X-PAYMENT header.
    This function extracts the payer's wallet address from it.

    For unpaid endpoints (like /health and /docs), returns None.

    Args:
        request: The incoming FastAPI request.

    Returns:
        The wallet address as a string, or None if not present.
    """
    # The x402 payment token is sent in the X-PAYMENT header.
    payment_header = request.headers.get("X-PAYMENT", "")

    if not payment_header:
        return None

    # In a real x402 implementation, the payment header is a JWT or
    # structured token. We extract the payer field from it.
    # For now, we also accept a plain wallet address for testing.
    # TODO: Parse the actual x402 payment token structure.
    return payment_header.split(":")[0] if ":" in payment_header else payment_header
