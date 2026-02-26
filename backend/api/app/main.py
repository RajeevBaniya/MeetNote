import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select, text

from app.core.config import get_database_url, get_jwt_secret
from app.core.redis import get_redis_url
from app.db.base import engine
from app.db.models import Meeting
from app.db.session import async_session_factory
from app.modules.auth.router import router as auth_router
from app.modules.join.router import router as join_router
from app.modules.meetings.router import router as meetings_router
from app.modules.meetings.events import publish_meeting_snapshot
from app.modules.stream_tokens.router import router as stream_tokens_router
from app.modules.chat.router import router as chat_router
from app.modules.chat.websocket import chat_websocket
from app.modules.transcripts.webhook import router as transcript_webhook_router
from app.modules.transcripts.websocket import transcript_websocket
from app.modules.transcripts.worker import run_transcript_worker
from app.state.client import close_redis, get_redis


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)

CORS_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000"]


async def run_db_migrations() -> None:
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text("ALTER TABLE users ADD COLUMN IF NOT EXISTS name VARCHAR(255) NULL")
            )
            await conn.execute(
                text(
                    "ALTER TABLE meetings "
                    "ADD COLUMN IF NOT EXISTS ended_at TIMESTAMPTZ NULL"
                )
            )
            await conn.execute(
                text(
                    "ALTER TABLE meetings "
                    "ADD COLUMN IF NOT EXISTS host_joined BOOLEAN NOT NULL DEFAULT FALSE"
                )
            )
            await conn.execute(
                text(
                    "ALTER TABLE meetings "
                    "ADD COLUMN IF NOT EXISTS original_host_id UUID NULL"
                )
            )
            await conn.execute(
                text(
                    "ALTER TABLE meetings "
                    "ADD COLUMN IF NOT EXISTS current_host_id UUID NULL"
                )
            )
            await conn.execute(
                text(
                    "UPDATE meetings "
                    "SET original_host_id = host_id "
                    "WHERE original_host_id IS NULL"
                )
            )
            await conn.execute(
                text(
                    "UPDATE meetings "
                    "SET current_host_id = host_id "
                    "WHERE current_host_id IS NULL"
                )
            )
            await conn.execute(
                text(
                    "ALTER TABLE meetings "
                    "ALTER COLUMN original_host_id SET NOT NULL"
                )
            )
            await conn.execute(
                text(
                    "ALTER TABLE meetings "
                    "ALTER COLUMN current_host_id SET NOT NULL"
                )
            )
    except Exception:
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    worker_task: asyncio.Task | None = None
    get_database_url()
    get_jwt_secret()
    if not get_redis_url():
        raise ValueError("REDIS_URL is required")
    await run_db_migrations()
    try:
        async with async_session_factory() as session:
            result = await session.execute(
                select(Meeting).where(Meeting.is_active.is_(True))
            )
            meetings = list(result.scalars().all())
        if meetings:
            await publish_meeting_snapshot([m.id for m in meetings])
        worker_task = asyncio.create_task(run_transcript_worker())
    except Exception:
        logging.debug("meeting_snapshot_startup_failed", exc_info=True)
    yield
    if worker_task is not None:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass
    await close_redis()


app = FastAPI(title="Smart Meeting API", version="0.1.0", lifespan=lifespan)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logging.exception("Unhandled exception: %s", exc)
    origin = request.headers.get("origin")
    if origin not in CORS_ORIGINS:
        origin = CORS_ORIGINS[0] if CORS_ORIGINS else "*"
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
        headers={
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        },
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(auth_router)
app.include_router(meetings_router)
app.include_router(join_router)
app.include_router(stream_tokens_router)
app.include_router(chat_router)
app.include_router(transcript_webhook_router)
app.websocket("/ws/meetings/{meeting_id}/chat")(chat_websocket)
app.websocket("/ws/meetings/{meeting_id}/transcript")(transcript_websocket)


@app.get("/health")
async def health_check() -> dict[str, str]:
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        pass
    if get_redis_url():
        try:
            redis = await get_redis()
            await redis.ping()
        except Exception:
            pass
    return {"status": "ok"}


if __name__ == "__main__":
    import os
    import uvicorn
    port = int(os.getenv("PORT", "8001"))
    uvicorn.run("app.main:app", host="127.0.0.1", port=port, reload=True)
