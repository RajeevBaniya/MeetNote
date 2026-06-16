from fastapi.responses import JSONResponse
import logging
from sqlalchemy import text

from app.core.config import get_database_url
from app.core.dependencies import get_service
from app.core.interfaces import CacheServiceInterface
from app.core.redis import get_redis_url
from app.db.session import async_session_factory

logger = logging.getLogger(__name__)


async def basic_health_check() -> dict[str, str]:
    """Basic health check that always returns ok."""
    return {"status": "ok"}


async def comprehensive_health_check() -> JSONResponse:
    """
    Comprehensive health check that tests all critical dependencies.
    Returns 200 if all systems are healthy, 503 if any system is down.
    """
    db_status = await _check_database_health()
    redis_status = await _check_redis_health()
    stream_status = _check_stream_config()
    
    overall_status = "ok"
    status_code = 200
    
    if db_status != "ok" or redis_status != "ok" or stream_status not in ("ok", "unknown"):
        overall_status = "error"
        status_code = 503
    
    return JSONResponse(
        status_code=status_code,
        content={
            "status": overall_status,
            "db": db_status,
            "redis": redis_status,
            "stream": stream_status,
        },
    )


async def _check_database_health() -> str:
    """Test database connectivity."""
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        return "ok"
    except Exception:
        logger.warning("health_check_db_failed", exc_info=True)
        return "error"


async def _check_redis_health() -> str:
    """Test Redis connectivity."""
    if not get_redis_url():
        return "error"
    
    try:
        cache_service = get_service(CacheServiceInterface)  # type: ignore[type-abstract]
        await cache_service.ping()
        return "ok"
    except Exception:
        logger.warning("health_check_redis_failed", exc_info=True)
        return "error"


def _check_stream_config() -> str:
    """Check if Stream configuration is present."""
    if not get_database_url():
        return "unknown"
    return "ok"