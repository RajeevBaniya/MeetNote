import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_cors_origins
from app.core.logging import configure_logging
from app.routers.email import router as email_router
from app.routers.export import router as export_router
from app.routers.summaries import router as summaries_router
from app.routers.summary import router as summary_router
from app.routers.upload import router as upload_router
from app.routers.jobs import router as jobs_router
from app.db.base import engine
from app.core.database_setup import ensure_database_schema
from app.services.worker import DocumentProcessingWorker

logger = logging.getLogger(__name__)

worker = DocumentProcessingWorker()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("running_startup_migrations")
    try:
        await ensure_database_schema(engine)
    except Exception as exc:
        logger.critical("startup_migration_failed", exc_info=exc)
        raise exc
    
    worker.start()
    yield
    await worker.stop()


app = FastAPI(title="Smart Meeting Summarize API", version="0.1.0", lifespan=lifespan)

configure_logging()



@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logging.getLogger(__name__).error(
        "unhandled_summarize_exception",
        exc_info=exc,
    )
    cors_origins = get_cors_origins()
    origin = request.headers.get("origin")
    if origin not in cors_origins:
        origin = cors_origins[0] if cors_origins else "*"
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error", "details": str(exc)},
        headers={
            "Access-Control-Allow-Origin": origin,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        },
    )


# Configure CORS
cors_origins = get_cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Include Routers
app.include_router(upload_router)
app.include_router(summary_router)
app.include_router(email_router)
app.include_router(summaries_router)
app.include_router(export_router)
app.include_router(jobs_router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Meeting Notes Summarize API is running"}


if __name__ == "__main__":
    import os
    import uvicorn
    # Default to 8002 for the FastAPI Summarize service
    port = int(os.getenv("PORT", "8002"))
    uvicorn.run("app.main:app", host="127.0.0.1", port=port, reload=True)
