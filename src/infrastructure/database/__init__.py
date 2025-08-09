"""Database configurations and models."""

from typing import TYPE_CHECKING, Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from .connection import get_db

if TYPE_CHECKING:
    from ..repositories import (
        DocumentRepositoryImpl,
        SessionRepositoryImpl,
        UserRepositoryImpl,
    )


async def get_user_repository(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> "UserRepositoryImpl":
    """Get user repository instance."""
    from ..repositories import UserRepositoryImpl

    return UserRepositoryImpl(session)


async def get_session_repository(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> "SessionRepositoryImpl":
    """Get session repository instance."""
    from ..repositories import SessionRepositoryImpl

    return SessionRepositoryImpl(session)


async def get_document_repository(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> "DocumentRepositoryImpl":
    """Get document repository instance."""
    from ..externals.file_storage import FileStorageService
    from ..repositories import DocumentRepositoryImpl

    file_storage = FileStorageService()
    return DocumentRepositoryImpl(session, file_storage)


__all__ = [
    "get_db",
    "get_user_repository",
    "get_session_repository",
    "get_document_repository",
]
