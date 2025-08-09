"""Use case for getting users list (admin only)."""

from dataclasses import dataclass

from ....domain.entities import User
from ....domain.repositories import UserRepository


@dataclass
class GetUsersListInput:
    """Input for get users list use case."""

    skip: int = 0
    limit: int = 100
    search: str | None = None


@dataclass
class GetUsersListOutput:
    """Output for get users list use case."""

    users: list[User]
    total: int
    skip: int
    limit: int


class GetUsersListUseCase:
    """Use case for getting users list (admin only)."""

    def __init__(self, user_repository: UserRepository) -> None:
        """Initialize get users list use case.

        Args:
            user_repository: User repository
        """
        self._user_repository = user_repository

    async def execute(self, input_data: GetUsersListInput) -> GetUsersListOutput:
        """Execute get users list use case.

        Args:
            input_data: Input data

        Returns:
            List of users with pagination

        Note:
            This use case should only be called by admin users.
            Authorization check should be done at the presentation layer.
        """
        # Get active users with pagination
        users = await self._user_repository.find_active_users(
            skip=input_data.skip, limit=input_data.limit
        )

        # Count total users (for pagination)
        # Since we don't have a count method yet, we'll use a simple approach
        # In production, you'd want to add a count method to the repository
        total = len(users)  # This is simplified, should query total from DB

        return GetUsersListOutput(
            users=users,
            total=total,
            skip=input_data.skip,
            limit=input_data.limit,
        )
