"""Tests for UserId value object."""

import uuid

import pytest

from src.domain.value_objects import UserId


class TestUserId:
    """Test cases for UserId value object."""

    def test_create_with_valid_uuid(self) -> None:
        """Test creating UserId with valid UUID string."""
        valid_uuid = str(uuid.uuid4())
        user_id = UserId(valid_uuid)

        assert user_id.value == valid_uuid
        assert str(user_id) == valid_uuid

    def test_create_with_invalid_uuid(self) -> None:
        """Test creating UserId with invalid UUID string."""
        with pytest.raises(ValueError, match="Invalid user ID format"):
            UserId("not-a-valid-uuid")

    def test_create_with_empty_string(self) -> None:
        """Test creating UserId with empty string."""
        with pytest.raises(ValueError, match="User ID cannot be empty"):
            UserId("")

    def test_generate_creates_valid_uuid(self) -> None:
        """Test generating a new UserId."""
        user_id = UserId.generate()

        # Should be a valid UUID
        uuid.UUID(user_id.value)  # This will raise if invalid
        assert isinstance(user_id, UserId)

    def test_immutability(self) -> None:
        """Test that UserId is immutable."""
        user_id = UserId.generate()

        with pytest.raises(AttributeError):
            user_id.value = "new-value"  # type: ignore

    def test_equality(self) -> None:
        """Test UserId equality."""
        uuid_str = str(uuid.uuid4())
        user_id1 = UserId(uuid_str)
        user_id2 = UserId(uuid_str)
        user_id3 = UserId.generate()

        assert user_id1 == user_id2
        assert user_id1 != user_id3
