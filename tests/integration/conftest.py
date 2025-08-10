"""Integration test configuration for PostgreSQL testing."""

import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.infrastructure.database.models import Base

# PostgreSQL test database URL (using the running pgvector container)
POSTGRES_TEST_URL = os.getenv(
    "TEST_DATABASE_URL", "postgresql+asyncpg://raguser:ragpass@localhost:5433/ragdb"
)


@pytest_asyncio.fixture(scope="function")
async def postgres_session() -> AsyncGenerator[AsyncSession, None]:
    """Create async database session for PostgreSQL testing."""
    engine = create_async_engine(POSTGRES_TEST_URL, echo=False)

    # Create all tables
    async with engine.begin() as conn:
        # Drop all tables with CASCADE to handle foreign key constraints
        await conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)

    async_session_maker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session_maker() as session:
        yield session
        await session.rollback()

    # Clean up
    await engine.dispose()


@pytest.fixture
def use_postgres(monkeypatch):
    """Fixture to mark tests that require PostgreSQL."""
    # This fixture can be used to skip tests when PostgreSQL is not available
    try:
        import asyncpg  # noqa
    except ImportError:
        pytest.skip("PostgreSQL tests require asyncpg")
