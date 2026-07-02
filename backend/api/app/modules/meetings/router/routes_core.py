"""Core meetings router: composes create, query, join, and share route modules."""

from fastapi import APIRouter

from .routes_create import router as create_router
from .routes_join import router as join_router
from .routes_query import router as query_router
from .routes_share import router as share_router
from .routes_delete import router as delete_router

router = APIRouter()

router.include_router(create_router)
router.include_router(query_router)
router.include_router(share_router)
router.include_router(join_router)
router.include_router(delete_router)
