"""User repository interface."""

from abc import ABC, abstractmethod

from ..entities import User
from ..value_objects import Email, UserId


class UserRepository(ABC):
    """Abstract repository interface for User entities."""

    @abstractmethod
    async def save(self, user: User) -> None:
        """Save a user entity.

        Args:
            user: The user entity to save

        Raises:
            RepositoryError: If the save operation fails
        """
        pass

    @abstractmethod
    async def find_by_id(self, user_id: UserId) -> User | None:
        """Find a user by ID.

        Args:
            user_id: The user ID to search for

        Returns:
            The user if found, None otherwise

        Raises:
            RepositoryError: If the find operation fails
        """
        pass

    @abstractmethod
    async def find_by_email(self, email: Email) -> User | None:
        """Find a user by email address.

        Args:
            email: The email address to search for

        Returns:
            The user if found, None otherwise

        Raises:
            RepositoryError: If the find operation fails
        """
        pass

    @abstractmethod
    async def find_all(self, skip: int = 0, limit: int = 100) -> list[User]:
        """Find all users with pagination.

        Args:
            skip: Number of users to skip
            limit: Maximum number of users to return

        Returns:
            List of users

        Raises:
            RepositoryError: If the find operation fails
        """
        pass

    @abstractmethod
    async def find_active_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        """Find all active users with pagination.

        Args:
            skip: Number of users to skip
            limit: Maximum number of users to return

        Returns:
            List of active users

        Raises:
            RepositoryError: If the find operation fails
        """
        pass

    @abstractmethod
    async def update(self, user: User) -> None:
        """Update a user entity.

        Args:
            user: The user entity to update

        Raises:
            RepositoryError: If the update operation fails
        """
        pass

    @abstractmethod
    async def delete(self, user_id: UserId) -> None:
        """Delete a user by ID.

        Args:
            user_id: The ID of the user to delete

        Raises:
            RepositoryError: If the delete operation fails
        """
        pass

    @abstractmethod
    async def exists_with_email(self, email: Email) -> bool:
        """Check if a user with the given email exists.

        Args:
            email: The email to check

        Returns:
            True if a user with the email exists, False otherwise

        Raises:
            RepositoryError: If the check operation fails
        """
        pass

    @abstractmethod
    async def count(self) -> int:
        """Count total number of users.

        Returns:
            The total number of users

        Raises:
            RepositoryError: If the count operation fails
        """
        pass

    @abstractmethod
    async def count_active(self) -> int:
        """Count total number of active users.

        Returns:
            The total number of active users

        Raises:
            RepositoryError: If the count operation fails
        """
        pass
