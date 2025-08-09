"""Use case for changing user password."""

from dataclasses import dataclass

from ....domain.exceptions.auth_exceptions import (
    AuthenticationException,
    UserNotFoundException,
)
from ....domain.repositories import UserRepository
from ....domain.services import PasswordHasher
from ....domain.value_objects import HashedPassword, UserId


@dataclass
class ChangePasswordInput:
    """Input for change password use case."""

    user_id: str
    current_password: str
    new_password: str


@dataclass
class ChangePasswordOutput:
    """Output for change password use case."""

    success: bool
    message: str


class ChangePasswordUseCase:
    """Use case for changing user password."""

    def __init__(
        self,
        user_repository: UserRepository,
        password_hasher: PasswordHasher,
    ) -> None:
        """Initialize change password use case.

        Args:
            user_repository: User repository
            password_hasher: Password hasher service
        """
        self._user_repository = user_repository
        self._password_hasher = password_hasher

    async def execute(self, input_data: ChangePasswordInput) -> ChangePasswordOutput:
        """Execute change password use case.

        Args:
            input_data: Input data

        Returns:
            Change password result

        Raises:
            UserNotFoundException: If user not found
            AuthenticationException: If current password is incorrect
            ValueError: If new password is invalid
        """
        # Validate new password
        if len(input_data.new_password) < 8:
            raise ValueError("Password must be at least 8 characters")

        # Find user
        user_id = UserId(input_data.user_id)
        user = await self._user_repository.find_by_id(user_id)
        if not user:
            raise UserNotFoundException(f"User {user_id} not found")

        # Verify current password
        if not self._password_hasher.verify(
            input_data.current_password, user.password.value
        ):
            raise AuthenticationException("Current password is incorrect")

        # Hash new password
        hashed_password = HashedPassword(
            self._password_hasher.hash(input_data.new_password)
        )

        # Update password
        user.update_password(hashed_password)

        # Save updated user
        await self._user_repository.update(user)

        return ChangePasswordOutput(
            success=True, message="Password changed successfully"
        )
