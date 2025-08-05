"""Session repository interface."""

from abc import ABC, abstractmethod

from ..entities import Session
from ..value_objects import UserId


class SessionRepository(ABC):
    """Abstract repository interface for Session entities."""

    @abstractmethod
    async def save(self, session: Session) -> None:
        """Save a session entity.

        Args:
            session: The session entity to save

        Raises:
            RepositoryError: If the save operation fails
        """
        pass

    @abstractmethod
    async def find_by_id(self, session_id: str) -> Session | None:
        """Find a session by ID.

        Args:
            session_id: The session ID to search for

        Returns:
            The session if found, None otherwise

        Raises:
            RepositoryError: If the find operation fails
        """
        pass

    @abstractmethod
    async def find_by_access_token(self, access_token: str) -> Session | None:
        """Find a session by access token.

        Args:
            access_token: The access token to search for

        Returns:
            The session if found, None otherwise

        Raises:
            RepositoryError: If the find operation fails
        """
        pass

    @abstractmethod
    async def find_by_refresh_token(self, refresh_token: str) -> Session | None:
        """Find a session by refresh token.

        Args:
            refresh_token: The refresh token to search for

        Returns:
            The session if found, None otherwise

        Raises:
            RepositoryError: If the find operation fails
        """
        pass

    @abstractmethod
    async def find_by_user_id(self, user_id: UserId) -> list[Session]:
        """Find all sessions for a user.

        Args:
            user_id: The user ID to search for

        Returns:
            List of sessions for the user

        Raises:
            RepositoryError: If the find operation fails
        """
        pass

    @abstractmethod
    async def update(self, session: Session) -> None:
        """Update a session entity.

        Args:
            session: The session entity to update

        Raises:
            RepositoryError: If the update operation fails
        """
        pass

    @abstractmethod
    async def delete(self, session_id: str) -> None:
        """Delete a session by ID.

        Args:
            session_id: The ID of the session to delete

        Raises:
            RepositoryError: If the delete operation fails
        """
        pass

    @abstractmethod
    async def delete_by_user_id(self, user_id: UserId) -> None:
        """Delete all sessions for a user.

        Args:
            user_id: The ID of the user whose sessions to delete

        Raises:
            RepositoryError: If the delete operation fails
        """
        pass

    @abstractmethod
    async def delete_expired(self) -> int:
        """Delete all expired sessions.

        Returns:
            The number of sessions deleted

        Raises:
            RepositoryError: If the delete operation fails
        """
        pass

    @abstractmethod
    async def count_active(self) -> int:
        """Count total number of active (non-expired) sessions.

        Returns:
            The total number of active sessions

        Raises:
            RepositoryError: If the count operation fails
        """
        pass

    @abstractmethod
    async def count_by_user_id(self, user_id: UserId) -> int:
        """Count sessions for a specific user.

        Args:
            user_id: The user ID to count sessions for

        Returns:
            The number of sessions for the user

        Raises:
            RepositoryError: If the count operation fails
        """
        pass
