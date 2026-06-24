import asyncio
import logging
import time
from typing import Dict, Tuple

from app.state.client import get_redis

logger = logging.getLogger(__name__)

_queue: asyncio.Queue[Tuple[str, int]] | None = None
_worker_started = False
_last_redis_error_ts: float | None = None
_ERROR_WINDOW_SECONDS = 60.0
_metrics_dropped_local: int = 0


def _should_log_redis_error() -> bool:
    global _last_redis_error_ts
    now = time.monotonic()
    if _last_redis_error_ts is None or now - _last_redis_error_ts >= _ERROR_WINDOW_SECONDS:
        _last_redis_error_ts = now
        return True
    return False


async def _metrics_worker() -> None:
    global _metrics_dropped_local
    last_flush = time.monotonic()
    flush_interval = 5.0
    while True:
        try:
            try:
                queue = _queue
                if queue is None:
                    await asyncio.sleep(1.0)
                    continue
                name, amount = await asyncio.wait_for(queue.get(), timeout=flush_interval)
                retries = 2
                for attempt in range(retries):
                    try:
                        redis = await get_redis()
                        key = f"metrics:{name}"
                        new_value = await redis.incrby(key, amount)
                        if new_value < 0:
                            await redis.set(key, 0)
                        break
                    except Exception as exc:
                        if _should_log_redis_error():
                            logger.warning(
                                "metrics_incr_failed",
                                extra={"metric": name, "attempt": attempt + 1},
                                exc_info=exc,
                            )
                        if attempt == retries - 1:
                            break
            except asyncio.TimeoutError:
                pass
            finally:
                if _queue is not None and not _queue.empty():
                    _queue.task_done()

            now = time.monotonic()
            if now - last_flush >= flush_interval and _metrics_dropped_local > 0:
                try:
                    redis = await get_redis()
                    await redis.incrby("metrics:metrics_dropped_total", _metrics_dropped_local)
                    _metrics_dropped_local = 0
                except Exception as exc:
                    if _should_log_redis_error():
                        logger.warning(
                            "metrics_dropped_flush_failed",
                            exc_info=exc,
                        )
                last_flush = now
        except Exception as exc:
            if _should_log_redis_error():
                logger.warning("metrics_worker_error", exc_info=exc)


def init_metrics_worker() -> None:
    global _queue, _worker_started
    if _worker_started:
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    _queue = asyncio.Queue(maxsize=10000)
    loop.create_task(_metrics_worker())
    _worker_started = True


def incr(name: str, amount: int = 1) -> None:
    if amount == 0:
        return
    if _queue is None:
        if _should_log_redis_error():
            logger.warning("metrics_queue_uninitialized")
        return
    try:
        _queue.put_nowait((name, amount))
    except asyncio.QueueFull:
        if _should_log_redis_error():
            logger.warning("metrics_queue_overflow")
        global _metrics_dropped_local
        _metrics_dropped_local += amount
    except Exception as exc:
        if _should_log_redis_error():
            logger.warning(
                "metrics_enqueue_failed",
                extra={"metric": name},
                exc_info=exc,
            )


async def set_gauge(name: str, value: int) -> None:
    """
    Sets a metrics gauge-like value in Redis directly.

    This is used for snapshot-style metrics (for example, startup counts).
    """
    try:
        redis = await get_redis()
        normalized = max(0, int(value))
        await redis.set(f"metrics:{name}", normalized)
    except Exception as exc:
        if _should_log_redis_error():
            logger.warning("metrics_set_gauge_failed", exc_info=exc)


async def snapshot() -> Dict[str, int]:
    try:
        redis = await get_redis()
    except Exception as exc:
        logger.warning("metrics_redis_unavailable", exc_info=exc)
        return {}
    metrics: Dict[str, int] = {}
    cursor: int = 0
    pattern = "metrics:*"
    try:
        while True:
            cursor, keys = await redis.scan(cursor=cursor, match=pattern, count=100)
            if not keys:
                if cursor == 0:
                    break
                continue
            values = await redis.mget(*keys)
            for key, value in zip(keys, values):
                if value is None:
                    continue
                name = key.removeprefix("metrics:")
                try:
                    metrics[name] = int(value)
                except (TypeError, ValueError):
                    continue
            if cursor == 0:
                break
    except Exception as exc:
        logger.warning("metrics_snapshot_failed", exc_info=exc)
    return metrics


