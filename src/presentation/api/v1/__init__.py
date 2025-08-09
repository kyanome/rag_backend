"""API version 1."""

from fastapi import APIRouter

from .admin import router as admin_router
from .auth import router as auth_router
from .documents import router as documents_router
from .embeddings import router as embeddings_router

v1_router = APIRouter(prefix="/v1")
v1_router.include_router(auth_router)
v1_router.include_router(documents_router)
v1_router.include_router(embeddings_router)
v1_router.include_router(admin_router)

__all__ = ["v1_router"]
