"""Use case for updating user profile."""

from dataclasses import dataclass

from ....domain.entities import User
from ....domain.exceptions.auth_exceptions import UserNotFoundException
from ....domain.repositories import UserRepository
from ....domain.value_objects import Email, UserId


@dataclass
class UpdateUserInput:
    """Input for update user use case."""

    user_id: str
    name: str | None = None
    email: str | None = None


@dataclass
class UpdateUserOutput:
    """Output for update user use case."""

    user: User


class UpdateUserUseCase:
    """Use case for updating user profile."""

    def __init__(self, user_repository: UserRepository) -> None:
        """Initialize update user use case.

        Args:
            user_repository: User repository
        """
        self._user_repository = user_repository

    async def execute(self, input_data: UpdateUserInput) -> UpdateUserOutput:
        """Execute update user use case.

        Args:
            input_data: Input data

        Returns:
            Updated user

        Raises:
            UserNotFoundException: If user not found
            ValueError: If email is invalid
        """
        # Find user
        user_id = UserId(input_data.user_id)
        user = await self._user_repository.find_by_id(user_id)
        if not user:
            raise UserNotFoundException(f"User {user_id} not found")

        # Update fields
        if input_data.name is not None:
            user.update_name(input_data.name)

        if input_data.email is not None:
            # Check if email is already taken by another user
            existing_user = await self._user_repository.find_by_email(
                Email(input_data.email)
            )
            if existing_user and existing_user.id != user.id:
                raise ValueError(f"Email {input_data.email} is already taken")

            user.update_email(Email(input_data.email))

        # Save updated user
        await self._user_repository.update(user)

        return UpdateUserOutput(user=user)
