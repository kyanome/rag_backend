"""Tests for refresh token use case."""

import uuid
from datetime import timedelta
from unittest.mock import AsyncMock, Mock

import pytest

from src.application.use_cases.auth import RefreshTokenUseCase
from src.application.use_cases.auth.refresh_token_use_case import (
    RefreshTokenInput,
    RefreshTokenOutput,
)
from src.domain.entities import Session, User
from src.domain.exceptions.auth_exceptions import (
    AuthenticationException,
)
from src.domain.repositories import SessionRepository, UserRepository
from src.domain.services import PasswordHasher
from src.domain.value_objects import Email, UserId, UserRole


class TestRefreshTokenUseCase:
    """Test cases for refresh token use case."""

    @pytest.fixture
    def mock_user_repository(self) -> Mock:
        """Create a mock user repository."""
        return Mock(spec=UserRepository)

    @pytest.fixture
    def mock_session_repository(self) -> Mock:
        """Create a mock session repository."""
        return Mock(spec=SessionRepository)

    @pytest.fixture
    def sample_user(self) -> User:
        """Create a sample user."""
        password_hasher = PasswordHasher()
        return User(
            id=UserId(value=str(uuid.uuid4())),
            email=Email(value="test@example.com"),
            hashed_password=password_hasher.hash_password("Password123!"),
            name="Test User",
            role=UserRole.editor(),
            is_active=True,
            is_email_verified=True,
        )

    @pytest.fixture
    def sample_session(self, sample_user: User) -> Session:
        """Create a sample session."""
        from src.application.services import JwtService
        from src.infrastructure.config.settings import get_settings

        jwt_service = JwtService(get_settings())
        session_id = str(uuid.uuid4())
        access_token, _ = jwt_service.create_access_token(
            sample_user.id, sample_user.email.value, sample_user.role
        )
        refresh_token, _ = jwt_service.create_refresh_token(sample_user.id, session_id)

        session = Session.create(
            user_id=sample_user.id,
            access_token=access_token,
            refresh_token=refresh_token,
            access_token_ttl=timedelta(minutes=15),
            refresh_token_ttl=timedelta(days=30),
        )
        session.id = session_id  # Set the session ID
        return session

    @pytest.fixture
    def refresh_token_use_case(
        self,
        mock_user_repository: Mock,
        mock_session_repository: Mock,
    ) -> RefreshTokenUseCase:
        """Create a refresh token use case instance."""
        from src.application.services import JwtService
        from src.infrastructure.config.settings import get_settings

        return RefreshTokenUseCase(
            user_repository=mock_user_repository,
            session_repository=mock_session_repository,
            jwt_service=JwtService(get_settings()),
        )

    @pytest.mark.asyncio
    async def test_refresh_token_successful(
        self,
        refresh_token_use_case: RefreshTokenUseCase,
        mock_user_repository: Mock,
        mock_session_repository: Mock,
        sample_user: User,
        sample_session: Session,
    ) -> None:
        """Test successful token refresh."""
        # Arrange
        refresh_token = sample_session.refresh_token

        mock_session_repository.find_by_id = AsyncMock(return_value=sample_session)
        mock_user_repository.find_by_id = AsyncMock(return_value=sample_user)
        mock_session_repository.save = AsyncMock()

        # Act
        input_data = RefreshTokenInput(refresh_token=refresh_token)
        result = await refresh_token_use_case.execute(input_data)

        # Assert
        assert isinstance(result, RefreshTokenOutput)
        assert result.access_token is not None
        assert result.refresh_token is not None
        # New tokens should be valid JWTs
        assert len(result.access_token) > 50
        assert len(result.refresh_token) > 50

        mock_session_repository.find_by_id.assert_called_once_with(sample_session.id)
        mock_user_repository.find_by_id.assert_called_once_with(sample_user.id)
        mock_session_repository.save.assert_called_once()

        # Verify session was updated
        updated_session = mock_session_repository.save.call_args[0][0]
        assert updated_session.access_token is not None
        assert updated_session.refresh_token is not None

    @pytest.mark.asyncio
    async def test_refresh_token_session_not_found(
        self,
        refresh_token_use_case: RefreshTokenUseCase,
        mock_session_repository: Mock,
    ) -> None:
        """Test refresh token when session is not found."""
        # Arrange
        from src.application.services import JwtService
        from src.infrastructure.config.settings import get_settings

        jwt_service = JwtService(get_settings())
        session_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        refresh_token, _ = jwt_service.create_refresh_token(
            UserId(value=user_id), session_id
        )

        mock_session_repository.find_by_id = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(AuthenticationException):
            input_data = RefreshTokenInput(refresh_token=refresh_token)
            await refresh_token_use_case.execute(input_data)

        mock_session_repository.find_by_id.assert_called_once_with(session_id)

    @pytest.mark.asyncio
    async def test_refresh_token_expired_refresh_token(
        self,
        refresh_token_use_case: RefreshTokenUseCase,
        mock_session_repository: Mock,
        sample_user: User,
    ) -> None:
        """Test refresh token when refresh token is expired."""
        # Arrange
        from src.application.services import JwtService
        from src.infrastructure.config.settings import get_settings

        jwt_service = JwtService(get_settings())
        session_id = str(uuid.uuid4())
        refresh_token, _ = jwt_service.create_refresh_token(sample_user.id, session_id)

        expired_session = Session.create(
            user_id=sample_user.id,
            access_token="access_" + str(uuid.uuid4()),
            refresh_token=refresh_token,
            refresh_token_ttl=timedelta(days=30),
        )
        expired_session.id = session_id
        # Manually set expired time
        from datetime import UTC, datetime

        expired_session.refresh_token_expires_at = datetime.now(UTC) - timedelta(
            hours=1
        )

        mock_session_repository.find_by_id = AsyncMock(return_value=expired_session)

        # Act & Assert
        with pytest.raises(AuthenticationException):
            input_data = RefreshTokenInput(refresh_token=expired_session.refresh_token)
            await refresh_token_use_case.execute(input_data)

    @pytest.mark.asyncio
    async def test_refresh_token_user_not_found(
        self,
        refresh_token_use_case: RefreshTokenUseCase,
        mock_user_repository: Mock,
        mock_session_repository: Mock,
        sample_session: Session,
    ) -> None:
        """Test refresh token when user is not found."""
        # Arrange
        refresh_token = sample_session.refresh_token

        mock_session_repository.find_by_id = AsyncMock(return_value=sample_session)
        mock_user_repository.find_by_id = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(AuthenticationException):
            input_data = RefreshTokenInput(refresh_token=refresh_token)
            await refresh_token_use_case.execute(input_data)

    @pytest.mark.asyncio
    async def test_refresh_token_inactive_user(
        self,
        refresh_token_use_case: RefreshTokenUseCase,
        mock_user_repository: Mock,
        mock_session_repository: Mock,
        sample_user: User,
        sample_session: Session,
    ) -> None:
        """Test refresh token for inactive user."""
        # Arrange
        refresh_token = sample_session.refresh_token
        sample_user.deactivate()

        mock_session_repository.find_by_id = AsyncMock(return_value=sample_session)
        mock_user_repository.find_by_id = AsyncMock(return_value=sample_user)

        # Act & Assert
        with pytest.raises(AuthenticationException):
            input_data = RefreshTokenInput(refresh_token=refresh_token)
            await refresh_token_use_case.execute(input_data)

    @pytest.mark.asyncio
    async def test_refresh_token_updates_activity(
        self,
        refresh_token_use_case: RefreshTokenUseCase,
        mock_user_repository: Mock,
        mock_session_repository: Mock,
        sample_user: User,
        sample_session: Session,
    ) -> None:
        """Test that refresh token updates session activity."""
        # Arrange
        refresh_token = sample_session.refresh_token
        ip_address = "192.168.1.100"
        user_agent = "New User Agent"
        old_last_activity = sample_session.last_accessed_at

        mock_session_repository.find_by_id = AsyncMock(return_value=sample_session)
        mock_user_repository.find_by_id = AsyncMock(return_value=sample_user)
        mock_session_repository.save = AsyncMock()

        # Act
        input_data = RefreshTokenInput(
            refresh_token=refresh_token,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        await refresh_token_use_case.execute(input_data)

        # Assert
        updated_session = mock_session_repository.save.call_args[0][0]
        assert updated_session.ip_address == ip_address
        assert updated_session.user_agent == user_agent
        assert updated_session.last_accessed_at > old_last_activity
