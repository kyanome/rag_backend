"""Tests for register user use case."""

from unittest.mock import AsyncMock, Mock

import pytest

from src.application.use_cases.auth import RegisterUserUseCase
from src.domain.entities import User
from src.domain.exceptions.auth_exceptions import UserAlreadyExistsException
from src.domain.repositories import UserRepository
from src.domain.value_objects import Email, UserRole


class TestRegisterUserUseCase:
    """Test cases for register user use case."""

    @pytest.fixture
    def mock_user_repository(self) -> Mock:
        """Create a mock user repository."""
        return Mock(spec=UserRepository)

    @pytest.fixture
    def register_user_use_case(
        self,
        mock_user_repository: Mock,
    ) -> RegisterUserUseCase:
        """Create a register user use case instance."""
        return RegisterUserUseCase(user_repository=mock_user_repository)

    @pytest.mark.asyncio
    async def test_register_user_successful(
        self,
        register_user_use_case: RegisterUserUseCase,
        mock_user_repository: Mock,
    ) -> None:
        """Test successful user registration."""
        # Arrange
        email = "newuser@example.com"
        password = "SecurePassword123!"
        name = "New User"
        role = UserRole.viewer()

        mock_user_repository.exists_with_email = AsyncMock(return_value=False)
        mock_user_repository.save = AsyncMock()

        # Act
        result = await register_user_use_case.execute(
            email=email,
            password=password,
            name=name,
            role=role,
        )

        # Assert
        assert result.email.value == email
        assert result.name == name
        assert result.role == role
        assert result.is_active is True
        assert result.is_email_verified is False
        assert result.verify_password(password) is True

        mock_user_repository.exists_with_email.assert_called_once_with(
            Email(value=email)
        )
        mock_user_repository.save.assert_called_once()

        # Verify saved user
        saved_user = mock_user_repository.save.call_args[0][0]
        assert isinstance(saved_user, User)
        assert saved_user.email.value == email
        assert saved_user.name == name

    @pytest.mark.asyncio
    async def test_register_user_email_already_exists(
        self,
        register_user_use_case: RegisterUserUseCase,
        mock_user_repository: Mock,
    ) -> None:
        """Test user registration with existing email."""
        # Arrange
        email = "existing@example.com"
        password = "SecurePassword123!"
        name = "Existing User"

        mock_user_repository.exists_with_email = AsyncMock(return_value=True)

        # Act & Assert
        with pytest.raises(UserAlreadyExistsException):
            await register_user_use_case.execute(
                email=email,
                password=password,
                name=name,
            )

        mock_user_repository.exists_with_email.assert_called_once()
        mock_user_repository.save.assert_not_called()

    @pytest.mark.asyncio
    async def test_register_user_with_default_role(
        self,
        register_user_use_case: RegisterUserUseCase,
        mock_user_repository: Mock,
    ) -> None:
        """Test user registration with default role."""
        # Arrange
        email = "defaultrole@example.com"
        password = "SecurePassword123!"
        name = "Default Role User"

        mock_user_repository.exists_with_email = AsyncMock(return_value=False)
        mock_user_repository.save = AsyncMock()

        # Act
        result = await register_user_use_case.execute(
            email=email,
            password=password,
            name=name,
            # No role specified, should use default
        )

        # Assert
        assert result.role.name.value == "viewer"  # Default role

    @pytest.mark.asyncio
    async def test_register_user_with_admin_role(
        self,
        register_user_use_case: RegisterUserUseCase,
        mock_user_repository: Mock,
    ) -> None:
        """Test user registration with admin role."""
        # Arrange
        email = "admin@example.com"
        password = "AdminPassword123!"
        name = "Admin User"
        role = UserRole.admin()

        mock_user_repository.exists_with_email = AsyncMock(return_value=False)
        mock_user_repository.save = AsyncMock()

        # Act
        result = await register_user_use_case.execute(
            email=email,
            password=password,
            name=name,
            role=role,
        )

        # Assert
        assert result.role == role
        assert result.role.name.value == "admin"

    @pytest.mark.asyncio
    async def test_register_user_password_hashing(
        self,
        register_user_use_case: RegisterUserUseCase,
        mock_user_repository: Mock,
    ) -> None:
        """Test that passwords are properly hashed."""
        # Arrange
        email = "hashing@example.com"
        password = "PlainTextPassword123!"
        name = "Hashing Test User"

        mock_user_repository.exists_with_email = AsyncMock(return_value=False)
        mock_user_repository.save = AsyncMock()

        # Act
        result = await register_user_use_case.execute(
            email=email,
            password=password,
            name=name,
        )

        # Assert
        # Password should be hashed, not plain text
        assert result.hashed_password.value != password
        assert len(result.hashed_password.value) > 0
        # But should still verify correctly
        assert result.verify_password(password) is True
        assert result.verify_password("WrongPassword") is False

    @pytest.mark.asyncio
    async def test_register_user_generates_unique_id(
        self,
        register_user_use_case: RegisterUserUseCase,
        mock_user_repository: Mock,
    ) -> None:
        """Test that each registered user gets a unique ID."""
        # Arrange
        mock_user_repository.exists_with_email = AsyncMock(return_value=False)
        mock_user_repository.save = AsyncMock()

        # Act - Register two users
        result1 = await register_user_use_case.execute(
            email="user1@example.com",
            password="Password123!",
            name="User 1",
        )

        result2 = await register_user_use_case.execute(
            email="user2@example.com",
            password="Password123!",
            name="User 2",
        )

        # Assert
        assert result1.id != result2.id
        assert len(result1.id.value) == 36  # UUID format
        assert len(result2.id.value) == 36
