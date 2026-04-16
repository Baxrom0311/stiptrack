from __future__ import annotations

import threading

from redis.asyncio import Redis

from app.core.config import settings

_redis_client: Redis | None = None
_lock = threading.Lock()


def get_redis() -> Redis:
    global _redis_client
    if _redis_client is None:
        with _lock:
            if _redis_client is None:
                _redis_client = Redis.from_url(
                    settings.redis_url,
                    decode_responses=True,
                )
    return _redis_client


async def ping_redis() -> bool:
    try:
        return await get_redis().ping()
    except Exception:
        return False
