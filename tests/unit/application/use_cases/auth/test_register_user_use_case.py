"""Tests for register user use case."""

from unittest.mock import AsyncMock, Mock

import pytest

from src.application.use_cases.auth import RegisterUserUseCase
from src.application.use_cases.auth.register_user_use_case import (
    RegisterUserInput,
    RegisterUserOutput,
)
from src.domain.entities import User
from src.domain.exceptions.auth_exceptions import UserAlreadyExistsException
from src.domain.repositories import UserRepository
from src.domain.value_objects import Email


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
        return RegisterUserUseCase(
            user_repository=mock_user_repository,
        )

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
        role = "viewer"

        mock_user_repository.find_by_email = AsyncMock(return_value=None)
        mock_user_repository.save = AsyncMock()

        # Act
        input_data = RegisterUserInput(
            email=email,
            password=password,
            name=name,
            role=role,
        )
        result = await register_user_use_case.execute(input_data)

        # Assert
        assert isinstance(result, RegisterUserOutput)
        assert result.success is True
        assert result.user.email.value == email
        assert result.user.name == name
        assert result.user.role.name.value == role
        assert result.user.is_active is True
        assert result.user.is_email_verified is False
        assert result.user.verify_password(password) is True

        mock_user_repository.find_by_email.assert_called_once_with(Email(value=email))
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

        # Create a mock existing user
        existing_user = Mock()
        mock_user_repository.find_by_email = AsyncMock(return_value=existing_user)

        # Act & Assert
        with pytest.raises(UserAlreadyExistsException):
            input_data = RegisterUserInput(
                email=email,
                password=password,
                name=name,
            )
            await register_user_use_case.execute(input_data)

        mock_user_repository.find_by_email.assert_called_once()
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

        mock_user_repository.find_by_email = AsyncMock(return_value=None)
        mock_user_repository.save = AsyncMock()

        # Act
        input_data = RegisterUserInput(
            email=email,
            password=password,
            name=name,
            # No role specified, should use default
        )
        result = await register_user_use_case.execute(input_data)

        # Assert
        assert result.user.role.name.value == "viewer"  # Default role

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
        role = "admin"

        mock_user_repository.find_by_email = AsyncMock(return_value=None)
        mock_user_repository.save = AsyncMock()

        # Act
        input_data = RegisterUserInput(
            email=email,
            password=password,
            name=name,
            role=role,
        )
        result = await register_user_use_case.execute(input_data)

        # Assert
        assert result.user.role.name.value == "admin"

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

        mock_user_repository.find_by_email = AsyncMock(return_value=None)
        mock_user_repository.save = AsyncMock()

        # Act
        input_data = RegisterUserInput(
            email=email,
            password=password,
            name=name,
        )
        result = await register_user_use_case.execute(input_data)

        # Assert
        # Password should be hashed, not plain text
        assert result.user.hashed_password.value != password
        assert len(result.user.hashed_password.value) > 0
        # But should still verify correctly
        assert result.user.verify_password(password) is True
        assert result.user.verify_password("WrongPassword") is False

    @pytest.mark.asyncio
    async def test_register_user_generates_unique_id(
        self,
        register_user_use_case: RegisterUserUseCase,
        mock_user_repository: Mock,
    ) -> None:
        """Test that each registered user gets a unique ID."""
        # Arrange
        mock_user_repository.find_by_email = AsyncMock(return_value=None)
        mock_user_repository.save = AsyncMock()

        # Act - Register two users
        input_data1 = RegisterUserInput(
            email="user1@example.com",
            password="Password123!",
            name="User 1",
        )
        result1 = await register_user_use_case.execute(input_data1)

        input_data2 = RegisterUserInput(
            email="user2@example.com",
            password="Password123!",
            name="User 2",
        )
        result2 = await register_user_use_case.execute(input_data2)

        # Assert
        assert result1.user.id != result2.user.id
        assert len(result1.user.id.value) == 36  # UUID format
        assert len(result2.user.id.value) == 36
