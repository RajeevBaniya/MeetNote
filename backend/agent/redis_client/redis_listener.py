import asyncio
import logging
from typing import Awaitable, Callable, Iterable

from redis.asyncio import Redis

logger = logging.getLogger(__name__)


async def listen_to_events(
    redis_client: Redis,
    channels: Iterable[str],
    should_shutdown: Callable[[], bool],
    handle_message: Callable[[str, str], Awaitable[None]],
) -> None:
    pubsub = redis_client.pubsub()

    await pubsub.subscribe(*channels)

    logger.info("Subscribed to Redis pub/sub channels")

    try:
        async for message in pubsub.listen():
            if should_shutdown():
                break

            if message["type"] != "message":
                continue

            channel = message["channel"]
            data = message["data"]
            await handle_message(channel, data)

    except asyncio.CancelledError:
        logger.info("Event listener cancelled")
        raise
    finally:
        await pubsub.unsubscribe()
        await pubsub.close()

