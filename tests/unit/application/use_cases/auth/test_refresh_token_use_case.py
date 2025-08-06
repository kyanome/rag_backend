"""Tests for refresh token use case."""

import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock

import pytest

from src.application.use_cases.auth import RefreshTokenUseCase
from src.domain.entities import Session, User
from src.domain.exceptions.auth_exceptions import (
    InvalidTokenException,
    SessionExpiredException,
    UserNotFoundException,
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
        return Session.create(
            user_id=sample_user.id,
            access_token="old_access_" + str(uuid.uuid4()),
            refresh_token="refresh_" + str(uuid.uuid4()),
            access_token_ttl=timedelta(minutes=15),
            refresh_token_ttl=timedelta(days=30),
        )

    @pytest.fixture
    def refresh_token_use_case(
        self,
        mock_user_repository: Mock,
        mock_session_repository: Mock,
    ) -> RefreshTokenUseCase:
        """Create a refresh token use case instance."""
        return RefreshTokenUseCase(
            user_repository=mock_user_repository,
            session_repository=mock_session_repository,
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

        mock_session_repository.find_by_refresh_token = AsyncMock(
            return_value=sample_session
        )
        mock_user_repository.find_by_id = AsyncMock(return_value=sample_user)
        mock_session_repository.update = AsyncMock()

        # Act
        result = await refresh_token_use_case.execute(refresh_token=refresh_token)

        # Assert
        assert result.access_token != sample_session.access_token  # New token
        assert result.refresh_token == sample_session.refresh_token  # Same refresh
        assert result.user_id == sample_user.id
        assert result.email == sample_user.email
        assert result.role == sample_user.role

        mock_session_repository.find_by_refresh_token.assert_called_once_with(
            refresh_token
        )
        mock_user_repository.find_by_id.assert_called_once_with(sample_user.id)
        mock_session_repository.update.assert_called_once()

        # Verify session was updated with new access token
        updated_session = mock_session_repository.update.call_args[0][0]
        assert updated_session.access_token != "old_access_" + str(uuid.uuid4())
        assert updated_session.refresh_token == sample_session.refresh_token

    @pytest.mark.asyncio
    async def test_refresh_token_session_not_found(
        self,
        refresh_token_use_case: RefreshTokenUseCase,
        mock_session_repository: Mock,
    ) -> None:
        """Test refresh token when session is not found."""
        # Arrange
        refresh_token = "nonexistent_refresh_token"

        mock_session_repository.find_by_refresh_token = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(InvalidTokenException):
            await refresh_token_use_case.execute(refresh_token=refresh_token)

        mock_session_repository.find_by_refresh_token.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_token_expired_refresh_token(
        self,
        refresh_token_use_case: RefreshTokenUseCase,
        mock_session_repository: Mock,
        sample_user: User,
    ) -> None:
        """Test refresh token when refresh token is expired."""
        # Arrange
        expired_session = Session.create(
            user_id=sample_user.id,
            access_token="access_" + str(uuid.uuid4()),
            refresh_token="expired_refresh_" + str(uuid.uuid4()),
            refresh_token_ttl=timedelta(seconds=-1),  # Already expired
        )

        mock_session_repository.find_by_refresh_token = AsyncMock(
            return_value=expired_session
        )

        # Act & Assert
        with pytest.raises(SessionExpiredException):
            await refresh_token_use_case.execute(
                refresh_token=expired_session.refresh_token
            )

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

        mock_session_repository.find_by_refresh_token = AsyncMock(
            return_value=sample_session
        )
        mock_user_repository.find_by_id = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(UserNotFoundException):
            await refresh_token_use_case.execute(refresh_token=refresh_token)

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

        mock_session_repository.find_by_refresh_token = AsyncMock(
            return_value=sample_session
        )
        mock_user_repository.find_by_id = AsyncMock(return_value=sample_user)

        # Act & Assert
        with pytest.raises(InvalidTokenException):
            await refresh_token_use_case.execute(refresh_token=refresh_token)

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
        old_last_activity = sample_session.last_activity_at

        mock_session_repository.find_by_refresh_token = AsyncMock(
            return_value=sample_session
        )
        mock_user_repository.find_by_id = AsyncMock(return_value=sample_user)
        mock_session_repository.update = AsyncMock()

        # Act
        await refresh_token_use_case.execute(
            refresh_token=refresh_token,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Assert
        updated_session = mock_session_repository.update.call_args[0][0]
        assert updated_session.ip_address == ip_address
        assert updated_session.user_agent == user_agent
        assert updated_session.last_activity_at > old_last_activity