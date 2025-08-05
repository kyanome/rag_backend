"""Logout use case implementation."""

from dataclasses import dataclass

from ....domain.exceptions.auth_exceptions import SessionNotFoundException
from ....domain.repositories import SessionRepository
from ....domain.value_objects import UserId


@dataclass
class LogoutInput:
    """Logout use case input."""

    user_id: UserId
    session_id: str | None = None
    access_token: str | None = None


@dataclass
class LogoutOutput:
    """Logout use case output."""

    success: bool
    sessions_invalidated: int


class LogoutUseCase:
    """Use case for user logout."""

    def __init__(self, session_repository: SessionRepository) -> None:
        """Initialize logout use case."""
        self.session_repository = session_repository

    async def execute(self, input_data: LogoutInput) -> LogoutOutput:
        """Execute logout use case.

        Can logout a specific session or all sessions for a user.

        Args:
            input_data: Logout input data

        Returns:
            Logout output with success status and number of invalidated sessions
        """
        sessions_invalidated = 0

        if input_data.session_id:
            # Logout specific session
            session = await self.session_repository.find_by_id(input_data.session_id)
            if not session:
                raise SessionNotFoundException(f"Session {input_data.session_id} not found")

            # Verify session belongs to user
            if session.user_id != input_data.user_id:
                raise SessionNotFoundException(f"Session {input_data.session_id} not found")

            # Delete session
            await self.session_repository.delete(input_data.session_id)
            sessions_invalidated = 1

        elif input_data.access_token:
            # Logout by access token
            session = await self.session_repository.find_by_access_token(
                input_data.access_token
            )
            if session and session.user_id == input_data.user_id:
                await self.session_repository.delete(session.id)
                sessions_invalidated = 1

        else:
            # Logout all sessions for user
            sessions = await self.session_repository.find_by_user_id(input_data.user_id)
            for session in sessions:
                await self.session_repository.delete(session.id)
                sessions_invalidated += 1

        return LogoutOutput(
            success=True,
            sessions_invalidated=sessions_invalidated,
        )

