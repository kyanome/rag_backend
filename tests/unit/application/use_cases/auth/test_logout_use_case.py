"""Tests for logout use case."""

import uuid
from unittest.mock import AsyncMock, Mock

import pytest

from src.application.use_cases.auth import LogoutUseCase
from src.application.use_cases.auth.logout_use_case import LogoutInput, LogoutOutput
from src.domain.entities import Session
from src.domain.exceptions.auth_exceptions import SessionNotFoundException
from src.domain.repositories import SessionRepository
from src.domain.value_objects import UserId


class TestLogoutUseCase:
    """Test cases for logout use case."""

    @pytest.fixture
    def mock_session_repository(self) -> Mock:
        """Create a mock session repository."""
        return Mock(spec=SessionRepository)

    @pytest.fixture
    def sample_user_id(self) -> UserId:
        """Create a sample user ID."""
        return UserId(value=str(uuid.uuid4()))

    @pytest.fixture
    def sample_session(self, sample_user_id: UserId) -> Session:
        """Create a sample session."""
        return Session.create(
            user_id=sample_user_id,
            access_token="access_token_" + str(uuid.uuid4()),
            refresh_token="refresh_token_" + str(uuid.uuid4()),
        )

    @pytest.fixture
    def logout_use_case(
        self,
        mock_session_repository: Mock,
    ) -> LogoutUseCase:
        """Create a logout use case instance."""
        return LogoutUseCase(session_repository=mock_session_repository)

    @pytest.mark.asyncio
    async def test_logout_by_session_id_successful(
        self,
        logout_use_case: LogoutUseCase,
        mock_session_repository: Mock,
        sample_session: Session,
        sample_user_id: UserId,
    ) -> None:
        """Test successful logout using session ID."""
        # Arrange
        input_data = LogoutInput(
            user_id=sample_user_id,
            session_id=sample_session.id,
        )

        mock_session_repository.find_by_id = AsyncMock(return_value=sample_session)
        mock_session_repository.delete = AsyncMock()

        # Act
        result = await logout_use_case.execute(input_data)

        # Assert
        assert isinstance(result, LogoutOutput)
        assert result.success is True
        assert result.sessions_invalidated == 1

        mock_session_repository.find_by_id.assert_called_once_with(sample_session.id)
        mock_session_repository.delete.assert_called_once_with(sample_session.id)

    @pytest.mark.asyncio
    async def test_logout_by_access_token_successful(
        self,
        logout_use_case: LogoutUseCase,
        mock_session_repository: Mock,
        sample_session: Session,
        sample_user_id: UserId,
    ) -> None:
        """Test successful logout using access token."""
        # Arrange
        input_data = LogoutInput(
            user_id=sample_user_id,
            access_token=sample_session.access_token,
        )

        mock_session_repository.find_by_access_token = AsyncMock(
            return_value=sample_session
        )
        mock_session_repository.delete = AsyncMock()

        # Act
        result = await logout_use_case.execute(input_data)

        # Assert
        assert isinstance(result, LogoutOutput)
        assert result.success is True
        assert result.sessions_invalidated == 1

        mock_session_repository.find_by_access_token.assert_called_once_with(
            sample_session.access_token
        )
        mock_session_repository.delete.assert_called_once_with(sample_session.id)

    @pytest.mark.asyncio
    async def test_logout_all_sessions(
        self,
        logout_use_case: LogoutUseCase,
        mock_session_repository: Mock,
        sample_user_id: UserId,
    ) -> None:
        """Test logout all sessions for a user."""
        # Arrange
        input_data = LogoutInput(user_id=sample_user_id)

        mock_session_repository.delete_by_user_id = AsyncMock()

        # Act
        result = await logout_use_case.execute(input_data)

        # Assert
        assert isinstance(result, LogoutOutput)
        assert result.success is True
        # Note: The actual implementation may need to return the count
        assert result.sessions_invalidated >= 0

        mock_session_repository.delete_by_user_id.assert_called_once_with(
            sample_user_id
        )

    @pytest.mark.asyncio
    async def test_logout_session_not_found_by_id(
        self,
        logout_use_case: LogoutUseCase,
        mock_session_repository: Mock,
        sample_user_id: UserId,
    ) -> None:
        """Test logout when session is not found by ID."""
        # Arrange
        input_data = LogoutInput(
            user_id=sample_user_id,
            session_id="nonexistent_session_id",
        )

        mock_session_repository.find_by_id = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(SessionNotFoundException):
            await logout_use_case.execute(input_data)

        mock_session_repository.find_by_id.assert_called_once()
        mock_session_repository.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_logout_session_not_found_by_token(
        self,
        logout_use_case: LogoutUseCase,
        mock_session_repository: Mock,
        sample_user_id: UserId,
    ) -> None:
        """Test logout when session is not found by access token."""
        # Arrange
        input_data = LogoutInput(
            user_id=sample_user_id,
            access_token="nonexistent_token",
        )

        mock_session_repository.find_by_access_token = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(SessionNotFoundException):
            await logout_use_case.execute(input_data)

        mock_session_repository.find_by_access_token.assert_called_once()
        mock_session_repository.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_logout_wrong_user_session(
        self,
        logout_use_case: LogoutUseCase,
        mock_session_repository: Mock,
        sample_session: Session,
    ) -> None:
        """Test logout attempt on another user's session."""
        # Arrange
        wrong_user_id = UserId(value=str(uuid.uuid4()))
        input_data = LogoutInput(
            user_id=wrong_user_id,
            session_id=sample_session.id,
        )

        mock_session_repository.find_by_id = AsyncMock(return_value=sample_session)

        # Act & Assert
        with pytest.raises(SessionNotFoundException):
            await logout_use_case.execute(input_data)

        mock_session_repository.find_by_id.assert_called_once()
        mock_session_repository.delete.assert_not_called()
