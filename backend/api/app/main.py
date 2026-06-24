import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import CORS_ORIGINS
from app.core.health_checks import basic_health_check, comprehensive_health_check
from app.core.logging import configure_logging
from app.core.metrics import snapshot
from app.core.request_id import RequestIdMiddleware
from app.core.startup_tasks import initialize_application
from app.modules.auth.refresh_router import router as auth_refresh_router
from app.modules.auth.router import router as auth_router
from app.modules.auth.ws_ticket import router as auth_ws_ticket_router
from app.modules.chat.router import router as chat_router
from app.modules.chat.websocket import chat_websocket
from app.modules.join.router import router as join_router
from app.modules.meetings.router import router as meetings_router
from app.modules.recordings.router import router as recordings_router
from app.modules.stream_tokens.router import router as stream_tokens_router
from app.modules.transcripts.webhook import router as transcript_webhook_router
from app.modules.transcripts.websocket import transcript_websocket
from app.state.client import close_redis

logger = logging.getLogger(__name__)



@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    worker_task = await initialize_application()
    yield
    if worker_task is not None:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass
    await close_redis()


app = FastAPI(title="Smart Meeting API", version="0.1.0", lifespan=lifespan)

configure_logging()
app.add_middleware(RequestIdMiddleware)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    logging.getLogger(__name__).error(
        "unhandled_exception",
        extra={"request_id": request_id},
        exc_info=exc,
    )
    origin = request.headers.get("origin")
    if origin not in CORS_ORIGINS:
        origin = CORS_ORIGINS[0] if CORS_ORIGINS else "*"
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error", "request_id": request_id},
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
app.include_router(auth_refresh_router)
app.include_router(auth_ws_ticket_router)
app.include_router(meetings_router)
app.include_router(join_router)
app.include_router(stream_tokens_router)
app.include_router(chat_router)
app.include_router(recordings_router)
app.include_router(transcript_webhook_router)
app.websocket("/ws/meetings/{meeting_id}/chat")(chat_websocket)
app.websocket("/ws/meetings/{meeting_id}/transcript")(transcript_websocket)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return await basic_health_check()


@app.get("/healthz/deep")
async def healthz_deep() -> JSONResponse:
    return await comprehensive_health_check()


@app.get("/health")
async def health() -> JSONResponse:
    try:
        resp = await comprehensive_health_check()
        data = json.loads(bytes(resp.body).decode("utf-8"))
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "redis": "fail", "db": "fail"},
        )

    redis_ok = data.get("redis") == "ok"
    db_ok = data.get("db") == "ok"
    ok = redis_ok and db_ok

    return JSONResponse(
        status_code=200 if ok else 503,
        content={
            "status": "ok" if ok else "degraded",
            "redis": "ok" if redis_ok else "fail",
            "db": "ok" if db_ok else "fail",
        },
    )


@app.get("/metrics")
async def metrics() -> Response:
    data = await snapshot()
    lines: list[str] = []
    for name, value in sorted(data.items()):
        try:
            numeric = int(value)
        except (TypeError, ValueError):
            continue
        lines.append(f"{name} {numeric}")
    body = "\n".join(lines) + ("\n" if lines else "")
    return Response(
        content=body,
        media_type="text/plain; version=0.0.4; charset=utf-8",
        status_code=200,
    )


if __name__ == "__main__":
    import uvicorn

    from app.core.config import PORT
    uvicorn.run("app.main:app", host="127.0.0.1", port=PORT, reload=True)
