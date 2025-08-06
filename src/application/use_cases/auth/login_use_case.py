"""Login use case implementation."""

from dataclasses import dataclass
from datetime import UTC, datetime

from ....domain.entities import Session, User
from ....domain.exceptions.auth_exceptions import AuthenticationException
from ....domain.repositories import SessionRepository, UserRepository
from ....domain.value_objects import Email
from ...services import JwtService


@dataclass
class LoginInput:
    """Login use case input."""

    email: str
    password: str
    ip_address: str | None = None
    user_agent: str | None = None


@dataclass
class LoginOutput:
    """Login use case output."""

    user: User
    access_token: str
    refresh_token: str
    session_id: str


class LoginUseCase:
    """Use case for user login."""

    def __init__(
        self,
        user_repository: UserRepository,
        session_repository: SessionRepository,
        jwt_service: JwtService,
    ) -> None:
        """Initialize login use case."""
        self.user_repository = user_repository
        self.session_repository = session_repository
        self.jwt_service = jwt_service

    async def execute(self, input_data: LoginInput) -> LoginOutput:
        """Execute login use case.

        Args:
            input_data: Login input data

        Returns:
            Login output with user, tokens, and session ID

        Raises:
            AuthenticationError: If authentication fails
            UserNotFoundError: If user does not exist
        """
        # Find user by email
        email = Email(input_data.email)
        user = await self.user_repository.find_by_email(email)
        if not user:
            raise AuthenticationException("Invalid email or password")

        # Verify password
        if not user.verify_password(input_data.password):
            raise AuthenticationException("Invalid email or password")

        # Check if user is active
        if not user.is_active:
            raise AuthenticationException("User account is not active")

        # Generate tokens
        access_token, access_expires = self.jwt_service.create_access_token(
            user_id=user.id,
            email=user.email.value,
            role=user.role,
        )
        refresh_token, refresh_expires = self.jwt_service.create_refresh_token(
            user_id=user.id,
            session_id="",  # Will be updated after session creation
        )

        # Create session
        now = datetime.now(UTC)
        session = Session.create(
            user_id=user.id,
            access_token=access_token,
            refresh_token=refresh_token,
            access_token_ttl=access_expires - now,
            refresh_token_ttl=refresh_expires - now,
            ip_address=input_data.ip_address,
            user_agent=input_data.user_agent,
        )

        # Update refresh token with session ID
        refresh_token, _ = self.jwt_service.create_refresh_token(
            user_id=user.id,
            session_id=session.id,
        )
        session.refresh_token = refresh_token

        # Save session
        await self.session_repository.save(session)

        # Update user last login
        user.update_last_login()
        await self.user_repository.save(user)

        return LoginOutput(
            user=user,
            access_token=access_token,
            refresh_token=refresh_token,
            session_id=session.id,
        )
