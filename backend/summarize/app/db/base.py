from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import DATABASE_URL_SUMMEREASE


class Base(DeclarativeBase):
    pass


def _async_url(url: str) -> tuple[str, bool]:
    need_ssl = "sslmode=require" in url or "sslmode=verify" in url.lower()
    if url.startswith("postgresql://") and "asyncpg" not in url:
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    parsed = urlparse(url)
    if not parsed.query:
        return url, need_ssl
    qs = parse_qs(parsed.query, keep_blank_values=True)
    for key in ("sslmode", "ssl", "channel_binding"):
        qs.pop(key, None)
    new_query = urlencode(qs, doseq=True) if qs else ""
    clean = urlunparse(parsed._replace(query=new_query))
    return clean, need_ssl


_db_url, _db_need_ssl = _async_url(DATABASE_URL_SUMMEREASE)
_connect_args = {"ssl": True} if _db_need_ssl else {}

engine = create_async_engine(
    _db_url,
    pool_pre_ping=True,
    echo=False,
    connect_args=_connect_args,
)
