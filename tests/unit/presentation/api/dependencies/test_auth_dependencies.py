"""Tests for authentication dependencies."""

import uuid
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from src.application.services import JwtService
from src.domain.entities import User
from src.domain.repositories import UserRepository
from src.domain.value_objects import Email, UserId, UserRole
from src.infrastructure.config.settings import Settings
from src.infrastructure.services import PasswordHasherImpl
from src.presentation.api.dependencies.auth import (
    get_current_user,
    get_current_user_id,
    get_jwt_service,
    require_role,
)


class TestAuthDependencies:
    """Test cases for authentication dependencies."""

    @pytest.fixture
    def settings(self) -> Settings:
        """Create test settings."""
        return Settings()

    @pytest.fixture
    def jwt_service(self, settings: Settings) -> JwtService:
        """Create a JWT service."""
        return JwtService(settings=settings)

    @pytest.fixture
    def mock_user_repository(self) -> Mock:
        """Create a mock user repository."""
        return Mock(spec=UserRepository)

    @pytest.fixture
    def sample_user(self) -> User:
        """Create a sample user."""
        password_hasher = PasswordHasherImpl()
        return User(
            id=UserId(value=str(uuid.uuid4())),
            email=Email(value="test@example.com"),
            hashed_password=password_hasher.hash_password("Password123!"),
            name="Test User",
            role=UserRole.editor(),
            is_active=True,
        )

    @pytest.fixture
    def valid_credentials(
        self, jwt_service: JwtService, sample_user: User
    ) -> HTTPAuthorizationCredentials:
        """Create valid HTTP Bearer credentials."""
        access_token, _ = jwt_service.create_access_token(
            sample_user.id, sample_user.email.value, sample_user.role
        )
        return HTTPAuthorizationCredentials(scheme="Bearer", credentials=access_token)

    @pytest.mark.asyncio
    async def test_get_jwt_service(self) -> None:
        """Test getting JWT service instance."""
        jwt_service = await get_jwt_service()
        assert isinstance(jwt_service, JwtService)

    @pytest.mark.asyncio
    async def test_get_current_user_id_valid_token(
        self,
        valid_credentials: HTTPAuthorizationCredentials,
        jwt_service: JwtService,
        sample_user: User,
    ) -> None:
        """Test extracting user ID from valid token."""
        # Act
        user_id = await get_current_user_id(valid_credentials, jwt_service)

        # Assert
        assert user_id == sample_user.id

    @pytest.mark.asyncio
    async def test_get_current_user_id_invalid_token(
        self,
        jwt_service: JwtService,
    ) -> None:
        """Test extracting user ID from invalid token."""
        # Arrange
        invalid_credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="invalid_token"
        )

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_id(invalid_credentials, jwt_service)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_get_current_user_id_missing_sub(
        self,
        jwt_service: JwtService,
        settings: Settings,
    ) -> None:
        """Test extracting user ID when 'sub' is missing from token."""
        # Create a token without 'sub' field
        from datetime import UTC, datetime, timedelta

        from jose import jwt

        payload = {
            "email": "test@example.com",
            "role": "viewer",
            "type": "access",
            "exp": datetime.now(UTC) + timedelta(minutes=15),
            "iat": datetime.now(UTC),
        }
        token = jwt.encode(
            payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
        )
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user_id(credentials, jwt_service)

        assert exc_info.value.status_code == 401
        assert "Invalid token payload" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_current_user_valid(
        self,
        mock_user_repository: Mock,
        sample_user: User,
    ) -> None:
        """Test getting current user with valid user ID."""
        # Arrange
        mock_user_repository.find_by_id = AsyncMock(return_value=sample_user)

        # Act
        result = await get_current_user(sample_user.id, mock_user_repository)

        # Assert
        assert result == sample_user
        mock_user_repository.find_by_id.assert_called_once_with(sample_user.id)

    @pytest.mark.asyncio
    async def test_get_current_user_not_found(
        self,
        mock_user_repository: Mock,
        sample_user: User,
    ) -> None:
        """Test getting current user when user is not found."""
        # Arrange
        mock_user_repository.find_by_id = AsyncMock(return_value=None)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(sample_user.id, mock_user_repository)

        assert exc_info.value.status_code == 401
        assert "User not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_current_user_inactive(
        self,
        mock_user_repository: Mock,
        sample_user: User,
    ) -> None:
        """Test getting current user when user is inactive."""
        # Arrange
        sample_user.deactivate()
        mock_user_repository.find_by_id = AsyncMock(return_value=sample_user)

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(sample_user.id, mock_user_repository)

        assert exc_info.value.status_code == 401
        assert "not active" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_require_role_single_role_allowed(
        self,
        sample_user: User,
    ) -> None:
        """Test role requirement with allowed role."""
        # Arrange
        sample_user.update_role(UserRole.admin())
        role_checker = require_role(UserRole.admin())

        # Act
        result = await role_checker(sample_user)

        # Assert
        assert result == sample_user

    @pytest.mark.asyncio
    async def test_require_role_single_role_denied(
        self,
        sample_user: User,
    ) -> None:
        """Test role requirement with denied role."""
        # Arrange
        sample_user.update_role(UserRole.viewer())
        role_checker = require_role(UserRole.admin())

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await role_checker(sample_user)

        assert exc_info.value.status_code == 403
        assert "Insufficient permissions" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_require_role_multiple_roles_allowed(
        self,
        sample_user: User,
    ) -> None:
        """Test role requirement with multiple allowed roles."""
        # Arrange
        sample_user.update_role(UserRole.editor())
        role_checker = require_role([UserRole.editor(), UserRole.admin()])

        # Act
        result = await role_checker(sample_user)

        # Assert
        assert result == sample_user

    @pytest.mark.asyncio
    async def test_require_role_multiple_roles_denied(
        self,
        sample_user: User,
    ) -> None:
        """Test role requirement with multiple roles all denied."""
        # Arrange
        sample_user.update_role(UserRole.viewer())
        role_checker = require_role([UserRole.editor(), UserRole.admin()])

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await role_checker(sample_user)

        assert exc_info.value.status_code == 403
