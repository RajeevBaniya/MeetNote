import logging
from fastapi import APIRouter

from .routes_core import router as core_router
from .routes_schedule import router as schedule_router
from .routes_assistant import router as assistant_router
from .routes_analytics import router as analytics_router
from .routes_transcript import router as transcript_router


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/meetings", tags=["meetings"])

router.include_router(core_router)
router.include_router(schedule_router)
router.include_router(assistant_router)
router.include_router(analytics_router)
router.include_router(transcript_router)

