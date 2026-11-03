"""
Async Redis Client Connection and Health Verification.
"""

import time
from functools import lru_cache

import redis.asyncio as aioredis
from redis.asyncio import Redis

from coordinator.config import get_settings

settings = get_settings()


@lru_cache
def get_redis_client() -> Redis:
    """Return async Redis client connected to configured redis URL."""
    return aioredis.from_url(
        settings.REDIS_URL,  # type: ignore[arg-type]
        encoding="utf-8",
        decode_responses=True,
    )


async def check_redis_health() -> dict[str, float | str | bool]:
    """Ping Redis server and measure round-trip response latency."""
    client = get_redis_client()
    start_time = time.perf_counter()
    try:
        pong = await client.ping()
        latency_ms = (time.perf_counter() - start_time) * 1000
        if pong:
            return {
                "status": "healthy",
                "connected": True,
                "latency_ms": round(latency_ms, 2),
            }
        return {
            "status": "unhealthy",
            "connected": False,
            "latency_ms": round(latency_ms, 2),
            "error": "Ping returned false",
        }
    except Exception as e:
        latency_ms = (time.perf_counter() - start_time) * 1000
        return {
            "status": "unhealthy",
            "connected": False,
            "latency_ms": round(latency_ms, 2),
            "error": str(e),
        }
