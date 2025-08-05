"""Tests for Email value object."""

import pytest

from src.domain.value_objects import Email


class TestEmail:
    """Test cases for Email value object."""

    def test_create_with_valid_email(self) -> None:
        """Test creating Email with valid email addresses."""
        valid_emails = [
            "user@example.com",
            "test.user@example.com",
            "user+tag@example.co.uk",
            "123@example.com",
            "user@subdomain.example.com",
        ]

        for email_str in valid_emails:
            email = Email(email_str)
            assert email.value == email_str.lower()
            assert str(email) == email_str.lower()

    def test_email_normalization(self) -> None:
        """Test that emails are normalized to lowercase."""
        email = Email("User@EXAMPLE.COM  ")
        assert email.value == "user@example.com"

    def test_create_with_invalid_email(self) -> None:
        """Test creating Email with invalid email addresses."""
        invalid_emails = [
            "notanemail",
            "@example.com",
            "user@",
            "user@.com",
            "user@example..com",
            "user name@example.com",
            "user@exam ple.com",
        ]

        for email_str in invalid_emails:
            with pytest.raises(ValueError, match="Invalid email format"):
                Email(email_str)

    def test_create_with_empty_string(self) -> None:
        """Test creating Email with empty string."""
        with pytest.raises(ValueError, match="Email cannot be empty"):
            Email("")

    def test_create_with_too_long_email(self) -> None:
        """Test creating Email with too long string."""
        long_email = "a" * 250 + "@example.com"
        with pytest.raises(ValueError, match="Email address too long"):
            Email(long_email)

    def test_immutability(self) -> None:
        """Test that Email is immutable."""
        email = Email("user@example.com")

        with pytest.raises(AttributeError):
            email.value = "new@example.com"  # type: ignore

    def test_equality(self) -> None:
        """Test Email equality."""
        email1 = Email("user@example.com")
        email2 = Email("USER@EXAMPLE.COM")
        email3 = Email("other@example.com")

        assert email1 == email2  # Case insensitive
        assert email1 != email3
