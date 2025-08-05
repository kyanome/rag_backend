"""UserRepository implementation using SQLAlchemy."""

from typing import cast

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import User
from src.domain.exceptions import RepositoryError
from src.domain.exceptions.auth_exceptions import UserNotFoundException
from src.domain.repositories import UserRepository
from src.domain.value_objects import Email, UserId

from ..database.models import UserModel


class UserRepositoryImpl(UserRepository):
    """Concrete implementation of UserRepository using SQLAlchemy."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize repository with database session.

        Args:
            session: AsyncSession instance for database operations
        """
        self.session = session

    async def save(self, user: User) -> None:
        """Save a user entity.

        Args:
            user: The user entity to save

        Raises:
            RepositoryError: If the save operation fails
        """
        try:
            # Convert domain entity to SQLAlchemy model
            user_model = UserModel.from_domain(user)

            # Check if user exists
            existing = await self.session.get(UserModel, user_model.id)
            if existing:
                # Update existing user
                for attr, value in user_model.__dict__.items():
                    if not attr.startswith("_"):
                        setattr(existing, attr, value)
            else:
                # Add new user
                self.session.add(user_model)

            await self.session.flush()
        except IntegrityError as e:
            if "email" in str(e.orig):
                raise RepositoryError(f"User with email {user.email.value} already exists") from e
            raise RepositoryError(f"Failed to save user: {str(e)}") from e
        except Exception as e:
            raise RepositoryError(f"Failed to save user: {str(e)}") from e

    async def find_by_id(self, user_id: UserId) -> User | None:
        """Find a user by ID.

        Args:
            user_id: The user ID to search for

        Returns:
            The user if found, None otherwise

        Raises:
            RepositoryError: If the find operation fails
        """
        try:
            user_model = await self.session.get(UserModel, user_id.value)
            return user_model.to_domain() if user_model else None
        except Exception as e:
            raise RepositoryError(f"Failed to find user by ID: {str(e)}") from e

    async def find_by_email(self, email: Email) -> User | None:
        """Find a user by email address.

        Args:
            email: The email address to search for

        Returns:
            The user if found, None otherwise

        Raises:
            RepositoryError: If the find operation fails
        """
        try:
            stmt = select(UserModel).where(UserModel.email == email.value)
            result = await self.session.execute(stmt)
            user_model = result.scalar_one_or_none()
            return user_model.to_domain() if user_model else None
        except Exception as e:
            raise RepositoryError(f"Failed to find user by email: {str(e)}") from e

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
        try:
            stmt = (
                select(UserModel)
                .order_by(UserModel.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            user_models = result.scalars().all()
            return [user_model.to_domain() for user_model in user_models]
        except Exception as e:
            raise RepositoryError(f"Failed to find all users: {str(e)}") from e

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
        try:
            stmt = (
                select(UserModel)
                .where(UserModel.is_active == True)  # noqa: E712
                .order_by(UserModel.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            user_models = result.scalars().all()
            return [user_model.to_domain() for user_model in user_models]
        except Exception as e:
            raise RepositoryError(f"Failed to find active users: {str(e)}") from e

    async def update(self, user: User) -> None:
        """Update a user entity.

        Args:
            user: The user entity to update

        Raises:
            RepositoryError: If the update operation fails
        """
        try:
            existing = await self.session.get(UserModel, user.id.value)
            if not existing:
                raise UserNotFoundException(f"User with ID {user.id.value} not found")

            # Update the model
            user_model = UserModel.from_domain(user)
            for attr, value in user_model.__dict__.items():
                if not attr.startswith("_"):
                    setattr(existing, attr, value)

            await self.session.flush()
        except UserNotFoundException:
            raise
        except IntegrityError as e:
            if "email" in str(e.orig):
                raise RepositoryError(f"User with email {user.email.value} already exists") from e
            raise RepositoryError(f"Failed to update user: {str(e)}") from e
        except Exception as e:
            raise RepositoryError(f"Failed to update user: {str(e)}") from e

    async def delete(self, user_id: UserId) -> None:
        """Delete a user by ID.

        Args:
            user_id: The ID of the user to delete

        Raises:
            RepositoryError: If the delete operation fails
        """
        try:
            user_model = await self.session.get(UserModel, user_id.value)
            if not user_model:
                raise UserNotFoundException(f"User with ID {user_id.value} not found")

            await self.session.delete(user_model)
            await self.session.flush()
        except UserNotFoundException:
            raise
        except Exception as e:
            raise RepositoryError(f"Failed to delete user: {str(e)}") from e

    async def exists_with_email(self, email: Email) -> bool:
        """Check if a user with the given email exists.

        Args:
            email: The email to check

        Returns:
            True if a user with the email exists, False otherwise

        Raises:
            RepositoryError: If the check operation fails
        """
        try:
            stmt = select(func.count()).select_from(UserModel).where(UserModel.email == email.value)
            result = await self.session.execute(stmt)
            count = cast(int, result.scalar())
            return count > 0
        except Exception as e:
            raise RepositoryError(f"Failed to check if email exists: {str(e)}") from e

    async def count(self) -> int:
        """Count total number of users.

        Returns:
            The total number of users

        Raises:
            RepositoryError: If the count operation fails
        """
        try:
            stmt = select(func.count()).select_from(UserModel)
            result = await self.session.execute(stmt)
            return cast(int, result.scalar())
        except Exception as e:
            raise RepositoryError(f"Failed to count users: {str(e)}") from e

    async def count_active(self) -> int:
        """Count total number of active users.

        Returns:
            The total number of active users

        Raises:
            RepositoryError: If the count operation fails
        """
        try:
            stmt = (
                select(func.count())
                .select_from(UserModel)
                .where(UserModel.is_active == True)  # noqa: E712
            )
            result = await self.session.execute(stmt)
            return cast(int, result.scalar())
        except Exception as e:
            raise RepositoryError(f"Failed to count active users: {str(e)}") from e
