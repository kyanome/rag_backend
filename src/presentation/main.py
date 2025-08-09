"""FastAPI application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..infrastructure.config.settings import get_settings
from ..infrastructure.database.connection import init_database
from .api.v1 import v1_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """アプリケーションのライフサイクル管理。

    Args:
        app: FastAPIアプリケーション

    Yields:
        None
    """
    # 起動時の処理
    settings = get_settings()
    settings.ensure_file_storage_path()
    await init_database()

    yield

    # 終了時の処理（必要に応じて追加）


app = FastAPI(
    title="RAG Backend API",
    description="Enterprise RAG system API",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS from settings
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods,
    allow_headers=settings.cors_allow_headers,
)

# APIルーターを登録 (v1_routerにはauthとdocumentsの両方が含まれる)
app.include_router(v1_router, prefix="/api")


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "RAG Backend API", "version": "0.1.0"}


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}
