from typing import Awaitable, cast

from redis.asyncio import Redis


async def redis_llen(redis: Redis, key: str) -> int:
    result = await cast(Awaitable[int], redis.llen(key))
    return int(result)


async def redis_lrange(
    redis: Redis, key: str, start: int = 0, end: int = -1
) -> list[str]:
    result = await cast(Awaitable[list[bytes | str]], redis.lrange(key, start, end))
    items: list[object] = list(result) if result else []
    return [
        item.decode("utf-8") if isinstance(item, bytes) else str(item)
        for item in items
    ]


async def redis_lindex(redis: Redis, key: str, index: int) -> str | None:
    result = await cast(Awaitable[bytes | str | None], redis.lindex(key, index))
    if result is None:
        return None
    return result.decode("utf-8") if isinstance(result, bytes) else str(result)


async def redis_rpush(redis: Redis, key: str, *values: str) -> None:
    await cast(Awaitable[int], redis.rpush(key, *values))


async def redis_lpush(redis: Redis, key: str, *values: str) -> None:
    await cast(Awaitable[int], redis.lpush(key, *values))


async def redis_lpop(redis: Redis, key: str) -> str | None:
    result = await cast(Awaitable[bytes | str | None], redis.lpop(key))
    if result is None:
        return None
    return result.decode("utf-8") if isinstance(result, bytes) else str(result)


async def redis_ltrim(redis: Redis, key: str, start: int, end: int) -> None:
    await cast(Awaitable[str], redis.ltrim(key, start, end))


async def redis_incr(redis: Redis, key: str) -> int:
    result = await cast(Awaitable[int], redis.incr(key))
    return int(result)


async def redis_set(
    redis: Redis,
    key: str,
    value: str,
    *,
    nx: bool = False,
    ex: int | None = None,
) -> bool:
    result = await cast(Awaitable[bool | None], redis.set(key, value, nx=nx, ex=ex))
    return result is not None


async def redis_get(redis: Redis, key: str) -> str | None:
    result = await cast(Awaitable[bytes | str | None], redis.get(key))
    if result is None:
        return None
    return result.decode("utf-8") if isinstance(result, bytes) else str(result)


async def redis_hget(redis: Redis, name: str, key: str) -> str | None:
    result = await cast(Awaitable[bytes | str | None], redis.hget(name, key))
    if result is None:
        return None
    return result.decode("utf-8") if isinstance(result, bytes) else str(result)


async def redis_hset(redis: Redis, name: str, key: str, value: str) -> None:
    await cast(Awaitable[int], redis.hset(name, key, value))


async def redis_hmget(
    redis: Redis, name: str, keys: list[str]
) -> list[str | None]:
    result = await cast(Awaitable[list[bytes | str | None]], redis.hmget(name, keys))
    items: list[object] = list(result) if result else []
    return [
        item.decode("utf-8") if isinstance(item, bytes) else (str(item) if item is not None else None)
        for item in items
    ]


async def redis_sadd(redis: Redis, key: str, *members: str) -> None:
    await cast(Awaitable[int], redis.sadd(key, *members))


async def redis_sismember(redis: Redis, key: str, member: str) -> bool:
    result = await cast(Awaitable[bool | None], redis.sismember(key, member))
    return bool(result)


async def redis_brpop(redis: Redis, key: str, timeout: int = 5) -> str | None:
    result = await cast(Awaitable[tuple[bytes | str, bytes | str] | None], redis.brpop(key, timeout=timeout))
    if result is None:
        return None
    _, value = result
    return value.decode("utf-8") if isinstance(value, bytes) else str(value)


async def redis_publish(redis: Redis, channel: str, message: str) -> None:
    await cast(Awaitable[int], redis.publish(channel, message))


async def redis_expire(redis: Redis, key: str, seconds: int) -> None:
    await cast(Awaitable[bool], redis.expire(key, seconds))


async def redis_delete(redis: Redis, *keys: str) -> None:
    await cast(Awaitable[int], redis.delete(*keys))
