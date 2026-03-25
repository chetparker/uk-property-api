"""
cache.py — Redis Caching Layer
================================
Caches API responses in Redis so repeat lookups for the same postcode
are instant instead of waiting 2–5 seconds for the Land Registry.

WHY REDIS?
    Redis is an in-memory database — it stores data in RAM, so reads are
    sub-millisecond. Railway offers a free Redis plugin you can add with
    one click. The data disappears when Redis restarts, which is fine for
    us since this is just a cache (the Land Registry is the real source).

HOW IT WORKS:
    1. Before hitting the Land Registry, we check Redis: "Do we already
       have results for this postcode?"
    2. If yes (a "cache hit"), we return the cached data instantly.
    3. If no (a "cache miss"), we fetch from Land Registry, store the
       result in Redis with a time-to-live (TTL), and return it.

GRACEFUL FALLBACK:
    If Redis is unavailable (not configured, crashed, etc.), the app
    works fine — it just fetches fresh data every time. No crash.
"""

import json
import logging
from typing import Any, Optional

import redis.asyncio as redis

from app.config import get_settings

logger = logging.getLogger(__name__)

# This holds our Redis connection. It's set up once when the app starts.
_redis_client: Optional[redis.Redis] = None


async def init_redis() -> None:
    """
    Connect to Redis. Called once when the FastAPI app starts up.

    If REDIS_URL is not set or the connection fails, we log a warning
    and continue without caching.
    """
    global _redis_client
    settings = get_settings()

    if not settings.redis_url:
        logger.warning("REDIS_URL not set — caching and rate limiting disabled")
        return

    try:
        _redis_client = redis.from_url(
            settings.redis_url,
            decode_responses=True,        # Return strings, not bytes.
            socket_connect_timeout=5,     # Don't hang if Redis is unreachable.
        )
        # Test the connection with a PING command.
        await _redis_client.ping()
        logger.info("Connected to Redis successfully")
    except Exception as e:
        logger.warning(f"Could not connect to Redis: {e} — running without cache")
        _redis_client = None


async def close_redis() -> None:
    """
    Cleanly close the Redis connection. Called when the app shuts down.
    """
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        logger.info("Redis connection closed")
        _redis_client = None


def get_redis() -> Optional[redis.Redis]:
    """
    Return the current Redis client (or None if not connected).
    Used by other modules like the rate limiter.
    """
    return _redis_client


async def cache_get(key: str) -> Optional[Any]:
    """
    Look up a key in Redis. Returns the parsed JSON data, or None if
    the key doesn't exist (cache miss) or Redis is unavailable.

    Args:
        key: The cache key, e.g. "sold-prices:SW1A 1AA:10"

    Returns:
        Parsed data (dict/list) on a cache hit, or None on a miss.
    """
    if _redis_client is None:
        return None

    try:
        raw = await _redis_client.get(key)
        if raw is not None:
            logger.debug(f"Cache HIT: {key}")
            return json.loads(raw)
        logger.debug(f"Cache MISS: {key}")
        return None
    except Exception as e:
        # If Redis fails, treat it as a cache miss — don't crash.
        logger.warning(f"Redis GET failed for key '{key}': {e}")
        return None


async def cache_set(key: str, data: Any, ttl: Optional[int] = None) -> None:
    """
    Store data in Redis with an optional TTL (time-to-live in seconds).
    After the TTL expires, Redis deletes the key automatically.

    Args:
        key:  The cache key.
        data: Any JSON-serialisable data (dict, list, etc.).
        ttl:  Seconds until this entry expires. Uses config default if None.
    """
    if _redis_client is None:
        return

    if ttl is None:
        ttl = get_settings().cache_ttl_seconds

    try:
        await _redis_client.setex(
            name=key,
            time=ttl,
            value=json.dumps(data),
        )
        logger.debug(f"Cache SET: {key} (TTL={ttl}s)")
    except Exception as e:
        logger.warning(f"Redis SET failed for key '{key}': {e}")


def make_cache_key(prefix: str, **kwargs) -> str:
    """
    Build a consistent cache key from a prefix and keyword arguments.

    Example:
        make_cache_key("sold-prices", postcode="SW1A 1AA", limit=10)
        → "sold-prices:SW1A 1AA:10"
    """
    parts = [prefix] + [str(v) for v in kwargs.values()]
    return ":".join(parts)
