import asyncio
import logging
import os
from collections.abc import Awaitable, Callable
from typing import Any

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration


logger = logging.getLogger(__name__)

_sentry_enabled = False


def initialize_error_monitoring() -> None:
    """
    Configure Sentry error monitoring if SENTRY_DSN is present.
    Safe to call multiple times; initialization will happen once.
    """
    global _sentry_enabled

    if _sentry_enabled:
        return

    dsn = os.getenv("SENTRY_DSN")
    if not dsn:
        return

    try:
        sentry_sdk.init(
            dsn=dsn,
            integrations=[FastApiIntegration()],
            traces_sample_rate=0.0,
            send_default_pii=False,
        )
    except Exception:
        logger.exception("sentry_init_failed")
        return

    _sentry_enabled = True
    logger.info("sentry_initialized")


WorkerFn = Callable[[], Awaitable[Any]]


async def run_worker_with_sentry(name: str, worker: WorkerFn) -> None:
    """
    Wrap a long-running worker coroutine so unexpected errors
    are logged and reported to Sentry before bubbling up.
    """
    try:
        await worker()
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("%s_unhandled_error", name)
        if _sentry_enabled and sentry_sdk.Hub.current.client is not None:
            sentry_sdk.capture_exception(exc)
        raise

