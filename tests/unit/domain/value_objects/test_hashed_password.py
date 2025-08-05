"""Tests for HashedPassword value object."""

import pytest

from src.domain.value_objects import HashedPassword


class TestHashedPassword:
    """Test cases for HashedPassword value object."""

    def test_create_from_plain_password(self) -> None:
        """Test creating HashedPassword from plain text."""
        plain_password = "SecurePassword123!"
        hashed = HashedPassword.from_plain_password(plain_password)

        assert hashed.value.startswith("$2")  # bcrypt prefix
        assert str(hashed) == "********"  # Masked representation

    def test_verify_correct_password(self) -> None:
        """Test verifying correct password."""
        plain_password = "SecurePassword123!"
        hashed = HashedPassword.from_plain_password(plain_password)

        assert hashed.verify(plain_password) is True

    def test_verify_incorrect_password(self) -> None:
        """Test verifying incorrect password."""
        plain_password = "SecurePassword123!"
        hashed = HashedPassword.from_plain_password(plain_password)

        assert hashed.verify("WrongPassword") is False

    def test_verify_empty_password(self) -> None:
        """Test verifying empty password."""
        hashed = HashedPassword.from_plain_password("SecurePassword123!")

        assert hashed.verify("") is False

    def test_create_with_short_password(self) -> None:
        """Test creating HashedPassword with too short password."""
        with pytest.raises(ValueError, match="Password must be at least 8 characters"):
            HashedPassword.from_plain_password("short")

    def test_create_with_empty_password(self) -> None:
        """Test creating HashedPassword with empty password."""
        with pytest.raises(ValueError, match="Password cannot be empty"):
            HashedPassword.from_plain_password("")

    def test_create_with_too_long_password(self) -> None:
        """Test creating HashedPassword with too long password."""
        long_password = "a" * 129
        with pytest.raises(ValueError, match="Password too long"):
            HashedPassword.from_plain_password(long_password)

    def test_create_with_existing_hash(self) -> None:
        """Test creating HashedPassword with existing bcrypt hash."""
        # First create a fresh hash
        plain_password = "test1234"
        fresh_hash = HashedPassword.from_plain_password(plain_password)

        # Now create another HashedPassword with that existing hash
        hashed = HashedPassword(fresh_hash.value)

        assert hashed.value == fresh_hash.value
        assert hashed.verify(plain_password) is True

    def test_create_with_invalid_hash(self) -> None:
        """Test creating HashedPassword with invalid hash format."""
        with pytest.raises(ValueError, match="Invalid hashed password format"):
            HashedPassword("not-a-bcrypt-hash")

    def test_create_with_empty_hash(self) -> None:
        """Test creating HashedPassword with empty hash."""
        with pytest.raises(ValueError, match="Hashed password cannot be empty"):
            HashedPassword("")

    def test_immutability(self) -> None:
        """Test that HashedPassword is immutable."""
        hashed = HashedPassword.from_plain_password("password123")

        with pytest.raises(AttributeError):
            hashed.value = "new-hash"  # type: ignore

    def test_different_hashes_for_same_password(self) -> None:
        """Test that same password generates different hashes."""
        plain_password = "SamePassword123!"
        hashed1 = HashedPassword.from_plain_password(plain_password)
        hashed2 = HashedPassword.from_plain_password(plain_password)

        # Hashes should be different (due to salt)
        assert hashed1.value != hashed2.value
        # But both should verify the same password
        assert hashed1.verify(plain_password) is True
        assert hashed2.verify(plain_password) is True
