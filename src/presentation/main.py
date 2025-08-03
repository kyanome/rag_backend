"""FastAPI application entry point."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..infrastructure.config.settings import get_settings
from ..infrastructure.database.connection import init_database
from .api.v1 import documents


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

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# APIルーターを登録
app.include_router(documents.router, prefix="/api/v1")


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "RAG Backend API", "version": "0.1.0"}


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}
