"""Shared ARQ Redis pool for API enqueue / job status."""

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from app.config import get_settings

_pool: ArqRedis | None = None


def get_redis_settings() -> RedisSettings:
    settings = get_settings()
    return RedisSettings(
        host=settings.redis_host,
        port=settings.redis_port,
        database=settings.redis_db,
    )


async def init_redis_pool() -> ArqRedis:
    global _pool
    if _pool is None:
        _pool = await create_pool(get_redis_settings())
    return _pool


async def close_redis_pool() -> None:
    global _pool
    if _pool is not None:
        close = getattr(_pool, "aclose", None)
        if close is not None:
            await close()
        else:
            await _pool.close()
        _pool = None


async def get_redis_pool() -> ArqRedis:
    if _pool is None:
        return await init_redis_pool()
    return _pool
