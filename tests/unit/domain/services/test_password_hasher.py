"""Tests for PasswordHasher domain service."""

import pytest

from src.domain.services import PasswordHasher
from src.domain.value_objects import HashedPassword


class TestPasswordHasher:
    """Test cases for PasswordHasher domain service."""

    def test_hash_password(self) -> None:
        """Test hashing a password."""
        plain_password = "SecurePassword123!"

        hashed = PasswordHasher.hash_password(plain_password)

        assert isinstance(hashed, HashedPassword)
        assert hashed.value.startswith("$2")
        assert hashed.verify(plain_password) is True

    def test_verify_password_correct(self) -> None:
        """Test verifying correct password."""
        plain_password = "SecurePassword123!"
        hashed = PasswordHasher.hash_password(plain_password)

        result = PasswordHasher.verify_password(plain_password, hashed)

        assert result is True

    def test_verify_password_incorrect(self) -> None:
        """Test verifying incorrect password."""
        hashed = PasswordHasher.hash_password("CorrectPassword123!")

        result = PasswordHasher.verify_password("WrongPassword123!", hashed)

        assert result is False

    def test_hash_password_validation(self) -> None:
        """Test password validation during hashing."""
        # Too short
        with pytest.raises(ValueError, match="Password must be at least 8 characters"):
            PasswordHasher.hash_password("short")

        # Empty
        with pytest.raises(ValueError, match="Password cannot be empty"):
            PasswordHasher.hash_password("")

        # Too long
        with pytest.raises(ValueError, match="Password too long"):
            PasswordHasher.hash_password("a" * 129)

    def test_different_hashes_for_same_password(self) -> None:
        """Test that same password generates different hashes."""
        plain_password = "SamePassword123!"

        hashed1 = PasswordHasher.hash_password(plain_password)
        hashed2 = PasswordHasher.hash_password(plain_password)

        # Hashes should be different (due to salt)
        assert hashed1.value != hashed2.value
        # But both should verify the same password
        assert PasswordHasher.verify_password(plain_password, hashed1) is True
        assert PasswordHasher.verify_password(plain_password, hashed2) is True
