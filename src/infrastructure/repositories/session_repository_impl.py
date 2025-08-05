"""SessionRepository implementation using SQLAlchemy."""

from datetime import UTC, datetime
from typing import cast

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import Session
from src.domain.exceptions import RepositoryError
from src.domain.exceptions.auth_exceptions import SessionExpiredException
from src.domain.repositories import SessionRepository
from src.domain.value_objects import UserId

from ..database.models import SessionModel


class SessionRepositoryImpl(SessionRepository):
    """Concrete implementation of SessionRepository using SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: AsyncSession instance for database operations
        """
        self.session = session

    async def save(self, session_entity: Session) -> None:
        """Save a session entity.

        Args:
            session_entity: The session entity to save

        Raises:
            RepositoryError: If the save operation fails
        """
        try:
            # Convert domain entity to SQLAlchemy model
            session_model = SessionModel.from_domain(session_entity)

            # Check if session exists
            existing = await self.session.get(SessionModel, session_model.id)
            if existing:
                # Update existing session
                for attr, value in session_model.__dict__.items():
                    if not attr.startswith("_"):
                        setattr(existing, attr, value)
            else:
                # Add new session
                self.session.add(session_model)

            await self.session.flush()
        except Exception as e:
            raise RepositoryError(f"Failed to save session: {str(e)}") from e

    async def find_by_id(self, session_id: str) -> Session | None:
        """Find a session by ID.

        Args:
            session_id: The session ID to search for

        Returns:
            The session if found, None otherwise

        Raises:
            RepositoryError: If the find operation fails
        """
        try:
            session_model = await self.session.get(SessionModel, session_id)
            return session_model.to_domain() if session_model else None
        except Exception as e:
            raise RepositoryError(f"Failed to find session by ID: {str(e)}") from e

    async def find_by_access_token(self, access_token: str) -> Session | None:
        """Find a session by access token.

        Args:
            access_token: The access token to search for

        Returns:
            The session if found, None otherwise

        Raises:
            RepositoryError: If the find operation fails
        """
        try:
            stmt = select(SessionModel).where(SessionModel.access_token == access_token)
            result = await self.session.execute(stmt)
            session_model = result.scalar_one_or_none()
            return session_model.to_domain() if session_model else None
        except Exception as e:
            raise RepositoryError(f"Failed to find session by access token: {str(e)}") from e

    async def find_by_refresh_token(self, refresh_token: str) -> Session | None:
        """Find a session by refresh token.

        Args:
            refresh_token: The refresh token to search for

        Returns:
            The session if found, None otherwise

        Raises:
            RepositoryError: If the find operation fails
        """
        try:
            stmt = select(SessionModel).where(SessionModel.refresh_token == refresh_token)
            result = await self.session.execute(stmt)
            session_model = result.scalar_one_or_none()
            return session_model.to_domain() if session_model else None
        except Exception as e:
            raise RepositoryError(f"Failed to find session by refresh token: {str(e)}") from e

    async def find_by_user_id(self, user_id: UserId) -> list[Session]:
        """Find all sessions for a user.

        Args:
            user_id: The user ID to search for

        Returns:
            List of sessions for the user

        Raises:
            RepositoryError: If the find operation fails
        """
        try:
            stmt = (
                select(SessionModel)
                .where(SessionModel.user_id == user_id.value)
                .order_by(SessionModel.created_at.desc())
            )
            result = await self.session.execute(stmt)
            session_models = result.scalars().all()
            return [session_model.to_domain() for session_model in session_models]
        except Exception as e:
            raise RepositoryError(f"Failed to find sessions by user ID: {str(e)}") from e

    async def update(self, session_entity: Session) -> None:
        """Update a session entity.

        Args:
            session_entity: The session entity to update

        Raises:
            RepositoryError: If the update operation fails
        """
        try:
            existing = await self.session.get(SessionModel, session_entity.id)
            if not existing:
                raise RepositoryError(f"Session with ID {session_entity.id} not found")

            # Check if session is expired
            if session_entity.is_expired():
                raise SessionExpiredException(f"Cannot update expired session {session_entity.id}")

            # Update the model
            session_model = SessionModel.from_domain(session_entity)
            for attr, value in session_model.__dict__.items():
                if not attr.startswith("_"):
                    setattr(existing, attr, value)

            await self.session.flush()
        except (RepositoryError, SessionExpiredException):
            raise
        except Exception as e:
            raise RepositoryError(f"Failed to update session: {str(e)}") from e

    async def delete(self, session_id: str) -> None:
        """Delete a session by ID.

        Args:
            session_id: The ID of the session to delete

        Raises:
            RepositoryError: If the delete operation fails
        """
        try:
            session_model = await self.session.get(SessionModel, session_id)
            if not session_model:
                # Session doesn't exist, but that's okay for delete
                return

            await self.session.delete(session_model)
            await self.session.flush()
        except Exception as e:
            raise RepositoryError(f"Failed to delete session: {str(e)}") from e

    async def delete_by_user_id(self, user_id: UserId) -> None:
        """Delete all sessions for a user.

        Args:
            user_id: The ID of the user whose sessions to delete

        Raises:
            RepositoryError: If the delete operation fails
        """
        try:
            stmt = delete(SessionModel).where(SessionModel.user_id == user_id.value)
            await self.session.execute(stmt)
            await self.session.flush()
        except Exception as e:
            raise RepositoryError(f"Failed to delete sessions for user: {str(e)}") from e

    async def delete_expired(self) -> int:
        """Delete all expired sessions.

        Returns:
            The number of sessions deleted

        Raises:
            RepositoryError: If the delete operation fails
        """
        try:
            now = datetime.now(UTC)
            stmt = delete(SessionModel).where(SessionModel.refresh_token_expires_at < now)
            result = await self.session.execute(stmt)
            await self.session.flush()
            return result.rowcount or 0
        except Exception as e:
            raise RepositoryError(f"Failed to delete expired sessions: {str(e)}") from e

    async def count_active(self) -> int:
        """Count total number of active (non-expired) sessions.

        Returns:
            The total number of active sessions

        Raises:
            RepositoryError: If the count operation fails
        """
        try:
            now = datetime.now(UTC)
            stmt = (
                select(func.count())
                .select_from(SessionModel)
                .where(SessionModel.refresh_token_expires_at >= now)
            )
            result = await self.session.execute(stmt)
            return cast(int, result.scalar())
        except Exception as e:
            raise RepositoryError(f"Failed to count active sessions: {str(e)}") from e

    async def count_by_user_id(self, user_id: UserId) -> int:
        """Count sessions for a specific user.

        Args:
            user_id: The user ID to count sessions for

        Returns:
            The number of sessions for the user

        Raises:
            RepositoryError: If the count operation fails
        """
        try:
            stmt = (
                select(func.count())
                .select_from(SessionModel)
                .where(SessionModel.user_id == user_id.value)
            )
            result = await self.session.execute(stmt)
            return cast(int, result.scalar())
        except Exception as e:
            raise RepositoryError(f"Failed to count sessions for user: {str(e)}") from e
