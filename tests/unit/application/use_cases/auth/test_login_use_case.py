"""Tests for login use case."""

import uuid
from unittest.mock import AsyncMock, Mock

import pytest

from src.application.services import JwtService
from src.application.use_cases.auth import LoginUseCase
from src.application.use_cases.auth.login_use_case import LoginInput, LoginOutput
from src.domain.entities import Session, User
from src.domain.exceptions.auth_exceptions import AuthenticationException
from src.domain.repositories import SessionRepository, UserRepository
from src.domain.services import PasswordHasher
from src.domain.value_objects import Email, UserId, UserRole


class TestLoginUseCase:
    """Test cases for login use case."""

    @pytest.fixture
    def mock_user_repository(self) -> Mock:
        """Create a mock user repository."""
        return Mock(spec=UserRepository)

    @pytest.fixture
    def mock_session_repository(self) -> Mock:
        """Create a mock session repository."""
        return Mock(spec=SessionRepository)

    @pytest.fixture
    def mock_jwt_service(self) -> Mock:
        """Create a mock JWT service."""
        return Mock(spec=JwtService)

    @pytest.fixture
    def password_hasher(self) -> PasswordHasher:
        """Create a password hasher."""
        return PasswordHasher()

    @pytest.fixture
    def sample_user(self, password_hasher: PasswordHasher) -> User:
        """Create a sample user."""
        return User(
            id=UserId(value=str(uuid.uuid4())),
            email=Email(value="test@example.com"),
            hashed_password=password_hasher.hash_password("Password123!"),
            name="Test User",
            role=UserRole.viewer(),
            is_active=True,
            is_email_verified=True,
        )

    @pytest.fixture
    def login_use_case(
        self,
        mock_user_repository: Mock,
        mock_session_repository: Mock,
        mock_jwt_service: Mock,
    ) -> LoginUseCase:
        """Create a login use case instance."""
        return LoginUseCase(
            user_repository=mock_user_repository,
            session_repository=mock_session_repository,
            jwt_service=mock_jwt_service,
        )

    @pytest.mark.asyncio
    async def test_login_successful(
        self,
        login_use_case: LoginUseCase,
        mock_user_repository: Mock,
        mock_session_repository: Mock,
        mock_jwt_service: Mock,
        sample_user: User,
    ) -> None:
        """Test successful login."""
        # Arrange
        input_data = LoginInput(
            email="test@example.com",
            password="Password123!",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        access_token = "test_access_token"
        refresh_token = "test_refresh_token"

        mock_user_repository.find_by_email = AsyncMock(return_value=sample_user)
        mock_jwt_service.create_access_token = Mock(return_value=(access_token, None))
        mock_jwt_service.create_refresh_token = Mock(return_value=(refresh_token, None))
        mock_session_repository.save = AsyncMock()

        # Act
        result = await login_use_case.execute(input_data)

        # Assert
        assert isinstance(result, LoginOutput)
        assert result.user == sample_user
        assert result.access_token == access_token
        assert result.refresh_token == refresh_token
        assert result.session_id is not None

        mock_user_repository.find_by_email.assert_called_once_with(
            Email(value=input_data.email)
        )
        mock_jwt_service.create_access_token.assert_called_once()
        mock_jwt_service.create_refresh_token.assert_called_once()
        mock_session_repository.save.assert_called_once()

        # Verify session was created correctly
        saved_session = mock_session_repository.save.call_args[0][0]
        assert isinstance(saved_session, Session)
        assert saved_session.user_id == sample_user.id
        assert saved_session.ip_address == input_data.ip_address
        assert saved_session.user_agent == input_data.user_agent

    @pytest.mark.asyncio
    async def test_login_invalid_email(
        self,
        login_use_case: LoginUseCase,
        mock_user_repository: Mock,
    ) -> None:
        """Test login with invalid email."""
        # Arrange
        input_data = LoginInput(
            email="nonexistent@example.com",
            password="Password123!",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        mock_user_repository.find_by_email = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(AuthenticationException):
            await login_use_case.execute(input_data)

        mock_user_repository.find_by_email.assert_called_once()

    @pytest.mark.asyncio
    async def test_login_invalid_password(
        self,
        login_use_case: LoginUseCase,
        mock_user_repository: Mock,
        sample_user: User,
    ) -> None:
        """Test login with invalid password."""
        # Arrange
        input_data = LoginInput(
            email="test@example.com",
            password="WrongPassword123!",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        mock_user_repository.find_by_email = AsyncMock(return_value=sample_user)

        # Act & Assert
        with pytest.raises(AuthenticationException):
            await login_use_case.execute(input_data)

        mock_user_repository.find_by_email.assert_called_once()

    @pytest.mark.asyncio
    async def test_login_inactive_user(
        self,
        login_use_case: LoginUseCase,
        mock_user_repository: Mock,
        sample_user: User,
    ) -> None:
        """Test login with inactive user."""
        # Arrange
        input_data = LoginInput(
            email="test@example.com",
            password="Password123!",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        # Make user inactive
        sample_user.deactivate()
        mock_user_repository.find_by_email = AsyncMock(return_value=sample_user)

        # Act & Assert
        with pytest.raises(AuthenticationException):
            await login_use_case.execute(input_data)

        mock_user_repository.find_by_email.assert_called_once()

    @pytest.mark.asyncio
    async def test_login_updates_last_login(
        self,
        login_use_case: LoginUseCase,
        mock_user_repository: Mock,
        mock_session_repository: Mock,
        mock_jwt_service: Mock,
        sample_user: User,
    ) -> None:
        """Test that login updates user's last login timestamp."""
        # Arrange
        input_data = LoginInput(
            email="test@example.com",
            password="Password123!",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        mock_user_repository.find_by_email = AsyncMock(return_value=sample_user)
        mock_user_repository.update = AsyncMock()
        mock_jwt_service.create_access_token = Mock(return_value=("token", None))
        mock_jwt_service.create_refresh_token = Mock(return_value=("refresh", None))
        mock_session_repository.save = AsyncMock()

        # Act
        await login_use_case.execute(input_data)

        # Assert
        mock_user_repository.update.assert_called_once_with(sample_user)
        assert sample_user.last_login_at is not None

    @pytest.mark.asyncio
    async def test_login_with_optional_parameters(
        self,
        login_use_case: LoginUseCase,
        mock_user_repository: Mock,
        mock_session_repository: Mock,
        mock_jwt_service: Mock,
        sample_user: User,
    ) -> None:
        """Test login with optional parameters (no IP/user agent)."""
        # Arrange
        input_data = LoginInput(
            email="test@example.com",
            password="Password123!",
            ip_address=None,
            user_agent=None,
        )

        mock_user_repository.find_by_email = AsyncMock(return_value=sample_user)
        mock_jwt_service.create_access_token = Mock(return_value=("token", None))
        mock_jwt_service.create_refresh_token = Mock(return_value=("refresh", None))
        mock_session_repository.save = AsyncMock()

        # Act
        result = await login_use_case.execute(input_data)

        # Assert
        assert result.access_token is not None
        assert result.refresh_token is not None

        saved_session = mock_session_repository.save.call_args[0][0]
        assert saved_session.ip_address is None
        assert saved_session.user_agent is None
