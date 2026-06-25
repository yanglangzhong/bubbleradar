import json
from typing import Any, Optional
import redis.asyncio as redis
from .config import get_settings

_settings = get_settings()
_redis_pool: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = redis.from_url(_settings.REDIS_URL, decode_responses=True)
    return _redis_pool


async def get_cache(key: str) -> Optional[Any]:
    r = await get_redis()
    value = await r.get(key)
    if value is None:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return value


async def set_cache(key: str, value: Any, expire: int = 60) -> None:
    r = await get_redis()
    await r.set(key, json.dumps(value, default=str), ex=expire)


async def delete_cache(key: str) -> None:
    r = await get_redis()
    await r.delete(key)
