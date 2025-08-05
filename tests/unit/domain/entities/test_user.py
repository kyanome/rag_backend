"""Tests for User entity."""

from datetime import datetime

import pytest

from src.domain.entities import User
from src.domain.value_objects import Email, HashedPassword, UserId, UserRole


class TestUser:
    """Test cases for User entity."""

    def test_create_user(self) -> None:
        """Test creating a user entity."""
        user_id = UserId.generate()
        email = Email("user@example.com")
        password = HashedPassword.from_plain_password("password123")
        role = UserRole.viewer()

        user = User(
            id=user_id,
            email=email,
            hashed_password=password,
            role=role,
        )

        assert user.id == user_id
        assert user.email == email
        assert user.hashed_password == password
        assert user.role == role
        assert user.is_active is True
        assert user.is_email_verified is False
        assert user.last_login_at is None
        assert isinstance(user.created_at, datetime)
        assert isinstance(user.updated_at, datetime)

    def test_verify_password(self) -> None:
        """Test password verification."""
        password = "SecurePassword123!"
        user = User(
            id=UserId.generate(),
            email=Email("user@example.com"),
            hashed_password=HashedPassword.from_plain_password(password),
            role=UserRole.viewer(),
        )

        assert user.verify_password(password) is True
        assert user.verify_password("WrongPassword") is False

    def test_update_password(self) -> None:
        """Test updating user password."""
        user = User(
            id=UserId.generate(),
            email=Email("user@example.com"),
            hashed_password=HashedPassword.from_plain_password("oldpassword"),
            role=UserRole.viewer(),
        )

        old_updated_at = user.updated_at
        new_password = HashedPassword.from_plain_password("newpassword123")

        user.update_password(new_password)

        assert user.hashed_password == new_password
        assert user.updated_at > old_updated_at

    def test_update_email(self) -> None:
        """Test updating user email."""
        user = User(
            id=UserId.generate(),
            email=Email("old@example.com"),
            hashed_password=HashedPassword.from_plain_password("password123"),
            role=UserRole.viewer(),
            is_email_verified=True,
        )

        old_updated_at = user.updated_at
        new_email = Email("new@example.com")

        user.update_email(new_email)

        assert user.email == new_email
        assert user.is_email_verified is False  # Reset verification
        assert user.updated_at > old_updated_at

    def test_update_role(self) -> None:
        """Test updating user role."""
        user = User(
            id=UserId.generate(),
            email=Email("user@example.com"),
            hashed_password=HashedPassword.from_plain_password("password123"),
            role=UserRole.viewer(),
        )

        old_updated_at = user.updated_at
        new_role = UserRole.editor()

        user.update_role(new_role)

        assert user.role == new_role
        assert user.updated_at > old_updated_at

    def test_activate_deactivate(self) -> None:
        """Test activating and deactivating user."""
        user = User(
            id=UserId.generate(),
            email=Email("user@example.com"),
            hashed_password=HashedPassword.from_plain_password("password123"),
            role=UserRole.viewer(),
            is_active=False,
        )

        assert user.is_active is False
        assert user.can_login() is False

        user.activate()
        assert user.is_active is True
        assert user.can_login() is True

        user.deactivate()
        assert user.is_active is False
        assert user.can_login() is False

    def test_verify_email_address(self) -> None:
        """Test email verification."""
        user = User(
            id=UserId.generate(),
            email=Email("user@example.com"),
            hashed_password=HashedPassword.from_plain_password("password123"),
            role=UserRole.viewer(),
        )

        assert user.is_email_verified is False

        user.verify_email()
        assert user.is_email_verified is True

    def test_record_login(self) -> None:
        """Test recording login timestamp."""
        user = User(
            id=UserId.generate(),
            email=Email("user@example.com"),
            hashed_password=HashedPassword.from_plain_password("password123"),
            role=UserRole.viewer(),
        )

        assert user.last_login_at is None

        user.record_login()
        assert user.last_login_at is not None
        assert isinstance(user.last_login_at, datetime)

    def test_invalid_type_validation(self) -> None:
        """Test validation of invalid types."""
        with pytest.raises(TypeError, match="id must be a UserId instance"):
            User(
                id="not-a-user-id",  # type: ignore
                email=Email("user@example.com"),
                hashed_password=HashedPassword.from_plain_password("password123"),
                role=UserRole.viewer(),
            )

        with pytest.raises(TypeError, match="email must be an Email instance"):
            User(
                id=UserId.generate(),
                email="not-an-email",  # type: ignore
                hashed_password=HashedPassword.from_plain_password("password123"),
                role=UserRole.viewer(),
            )

        with pytest.raises(TypeError, match="hashed_password must be a HashedPassword"):
            User(
                id=UserId.generate(),
                email=Email("user@example.com"),
                hashed_password="not-a-password",  # type: ignore
                role=UserRole.viewer(),
            )

        with pytest.raises(TypeError, match="role must be a UserRole instance"):
            User(
                id=UserId.generate(),
                email=Email("user@example.com"),
                hashed_password=HashedPassword.from_plain_password("password123"),
                role="not-a-role",  # type: ignore
            )

    def test_string_representation(self) -> None:
        """Test string representation of user."""
        user_id = UserId.generate()
        email = Email("user@example.com")
        role = UserRole.admin()

        user = User(
            id=user_id,
            email=email,
            hashed_password=HashedPassword.from_plain_password("password123"),
            role=role,
        )

        expected = f"User({user_id}, {email}, role={role})"
        assert str(user) == expected
