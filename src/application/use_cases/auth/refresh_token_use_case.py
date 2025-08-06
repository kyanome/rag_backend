"""Refresh token use case implementation."""

from dataclasses import dataclass

from jose import JWTError  # type: ignore[import-untyped]

from ....domain.exceptions.auth_exceptions import (
    AuthenticationException,
    SessionNotFoundException,
)
from ....domain.repositories import SessionRepository, UserRepository
from ...services import JwtService


@dataclass
class RefreshTokenInput:
    """Refresh token use case input."""

    refresh_token: str
    ip_address: str | None = None
    user_agent: str | None = None


@dataclass
class RefreshTokenOutput:
    """Refresh token use case output."""

    access_token: str
    refresh_token: str


class RefreshTokenUseCase:
    """Use case for refreshing access tokens."""

    def __init__(
        self,
        session_repository: SessionRepository,
        user_repository: UserRepository,
        jwt_service: JwtService,
    ) -> None:
        """Initialize refresh token use case."""
        self.session_repository = session_repository
        self.user_repository = user_repository
        self.jwt_service = jwt_service

    async def execute(self, input_data: RefreshTokenInput) -> RefreshTokenOutput:
        """Execute refresh token use case.

        Args:
            input_data: Refresh token input data

        Returns:
            New access and refresh tokens

        Raises:
            AuthenticationError: If refresh token is invalid
            SessionNotFoundError: If session does not exist
        """
        # Verify and decode refresh token
        try:
            payload = self.jwt_service.verify_refresh_token(input_data.refresh_token)
            session_id = payload.get("session_id")
            user_id_str = payload.get("sub")
        except JWTError as e:
            raise AuthenticationException(f"Invalid refresh token: {str(e)}") from e

        if not session_id or not user_id_str:
            raise AuthenticationException("Invalid refresh token payload")

        # Find session
        session = await self.session_repository.find_by_id(session_id)
        if not session:
            raise SessionNotFoundException(f"Session {session_id} not found")

        # Verify session is not expired
        if session.is_expired():
            await self.session_repository.delete(session_id)
            raise AuthenticationException("Session has expired")

        # Verify refresh token matches
        if session.refresh_token != input_data.refresh_token:
            # Possible token reuse attack - invalidate session
            await self.session_repository.delete(session_id)
            raise AuthenticationException("Invalid refresh token")

        # Get user
        user = await self.user_repository.find_by_id(session.user_id)
        if not user:
            await self.session_repository.delete(session_id)
            raise AuthenticationException("User not found")

        # Check if user is still active
        if not user.is_active:
            await self.session_repository.delete(session_id)
            raise AuthenticationException("User account is not active")

        # Generate new tokens
        new_access_token, access_expires = self.jwt_service.create_access_token(
            user_id=user.id,
            email=user.email.value,
            role=user.role,
        )
        new_refresh_token, _ = self.jwt_service.create_refresh_token(
            user_id=user.id,
            session_id=session.id,
        )

        # Update session with new tokens
        session.refresh(
            new_access_token=new_access_token,
            access_token_ttl=access_expires - session.last_accessed_at,
        )
        session.refresh_token = new_refresh_token
        session.update_activity(
            ip_address=input_data.ip_address,
            user_agent=input_data.user_agent,
        )

        # Save updated session
        await self.session_repository.save(session)

        return RefreshTokenOutput(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
        )
