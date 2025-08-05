"""Tests for Session entity."""

from datetime import UTC, datetime, timedelta

import pytest

from src.domain.entities import Session
from src.domain.value_objects import UserId


class TestSession:
    """Test cases for Session entity."""

    def test_create_session_with_factory(self) -> None:
        """Test creating session with factory method."""
        user_id = UserId.generate()
        access_token = "access-token-123"
        refresh_token = "refresh-token-456"

        session = Session.create(
            user_id=user_id,
            access_token=access_token,
            refresh_token=refresh_token,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        assert session.user_id == user_id
        assert session.access_token == access_token
        assert session.refresh_token == refresh_token
        assert session.ip_address == "192.168.1.1"
        assert session.user_agent == "Mozilla/5.0"
        assert session.is_access_token_expired() is False
        assert session.is_refresh_token_expired() is False
        assert session.is_expired() is False

    def test_create_session_direct(self) -> None:
        """Test creating session directly."""
        user_id = UserId.generate()
        now = datetime.now(UTC)

        session = Session(
            id="session-123",
            user_id=user_id,
            access_token="access-token",
            refresh_token="refresh-token",
            access_token_expires_at=now + timedelta(minutes=15),
            refresh_token_expires_at=now + timedelta(days=30),
        )

        assert session.id == "session-123"
        assert session.user_id == user_id

    def test_expired_access_token(self) -> None:
        """Test detecting expired access token."""
        # Create session with factory method first, then manipulate the expiration
        session = Session.create(
            user_id=UserId.generate(),
            access_token="access-token",
            refresh_token="refresh-token",
        )

        # Manually set the access token to expired
        now = datetime.now(UTC)
        session.access_token_expires_at = now - timedelta(minutes=1)

        assert session.is_access_token_expired() is True
        assert session.is_refresh_token_expired() is False
        assert session.is_expired() is False  # Session not expired, only access token
        assert session.can_refresh() is True

    def test_expired_refresh_token(self) -> None:
        """Test detecting expired refresh token."""
        # Create session with factory method first
        session = Session.create(
            user_id=UserId.generate(),
            access_token="access-token",
            refresh_token="refresh-token",
        )

        # Manually set both tokens to expired
        now = datetime.now(UTC)
        session.access_token_expires_at = now - timedelta(minutes=1)
        session.refresh_token_expires_at = now - timedelta(days=1)

        assert session.is_access_token_expired() is True
        assert session.is_refresh_token_expired() is True
        assert session.is_expired() is True
        assert session.can_refresh() is False

    def test_refresh_access_token(self) -> None:
        """Test refreshing access token."""
        session = Session.create(
            user_id=UserId.generate(),
            access_token="old-access-token",
            refresh_token="refresh-token",
        )

        old_access_token = session.access_token
        old_expiry = session.access_token_expires_at

        session.refresh("new-access-token")

        assert session.access_token == "new-access-token"
        assert session.access_token != old_access_token
        assert session.access_token_expires_at > old_expiry
        assert session.is_access_token_expired() is False

    def test_refresh_expired_session(self) -> None:
        """Test refreshing expired session."""
        # Create session with factory method first
        session = Session.create(
            user_id=UserId.generate(),
            access_token="access-token",
            refresh_token="refresh-token",
        )

        # Manually expire the refresh token
        now = datetime.now(UTC)
        session.refresh_token_expires_at = now - timedelta(days=1)

        with pytest.raises(ValueError, match="Cannot refresh expired session"):
            session.refresh("new-access-token")

    def test_extend_refresh_token(self) -> None:
        """Test extending refresh token expiration."""
        session = Session.create(
            user_id=UserId.generate(),
            access_token="access-token",
            refresh_token="refresh-token",
        )

        old_expiry = session.refresh_token_expires_at

        session.extend_refresh_token()

        assert session.refresh_token_expires_at > old_expiry

    def test_extend_expired_refresh_token(self) -> None:
        """Test extending expired refresh token."""
        # Create session with factory method first
        session = Session.create(
            user_id=UserId.generate(),
            access_token="access-token",
            refresh_token="refresh-token",
        )

        # Manually expire the refresh token
        now = datetime.now(UTC)
        session.refresh_token_expires_at = now - timedelta(days=1)

        with pytest.raises(ValueError, match="Cannot extend expired refresh token"):
            session.extend_refresh_token()

    def test_update_activity(self) -> None:
        """Test updating session activity."""
        session = Session.create(
            user_id=UserId.generate(),
            access_token="access-token",
            refresh_token="refresh-token",
        )

        old_last_accessed = session.last_accessed_at

        session.update_activity(
            ip_address="10.0.0.1",
            user_agent="Chrome/100.0",
        )

        assert session.ip_address == "10.0.0.1"
        assert session.user_agent == "Chrome/100.0"
        assert session.last_accessed_at > old_last_accessed

    def test_validation_errors(self) -> None:
        """Test validation errors."""
        now = datetime.now(UTC)
        user_id = UserId.generate()

        # Empty session ID
        with pytest.raises(ValueError, match="Session ID cannot be empty"):
            Session(
                id="",
                user_id=user_id,
                access_token="token",
                refresh_token="token",
                access_token_expires_at=now + timedelta(minutes=15),
                refresh_token_expires_at=now + timedelta(days=30),
            )

        # Invalid user_id type
        with pytest.raises(TypeError, match="user_id must be a UserId instance"):
            Session(
                id="session-123",
                user_id="not-a-user-id",  # type: ignore
                access_token="token",
                refresh_token="token",
                access_token_expires_at=now + timedelta(minutes=15),
                refresh_token_expires_at=now + timedelta(days=30),
            )

        # Empty access token
        with pytest.raises(ValueError, match="Access token cannot be empty"):
            Session(
                id="session-123",
                user_id=user_id,
                access_token="",
                refresh_token="token",
                access_token_expires_at=now + timedelta(minutes=15),
                refresh_token_expires_at=now + timedelta(days=30),
            )

        # Access token already expired
        with pytest.raises(
            ValueError, match="Access token expiration must be in the future"
        ):
            Session(
                id="session-123",
                user_id=user_id,
                access_token="token",
                refresh_token="token",
                access_token_expires_at=now - timedelta(minutes=1),
                refresh_token_expires_at=now + timedelta(days=30),
            )

        # Refresh token expires before access token
        with pytest.raises(
            ValueError, match="Refresh token must expire after access token"
        ):
            Session(
                id="session-123",
                user_id=user_id,
                access_token="token",
                refresh_token="token",
                access_token_expires_at=now + timedelta(days=30),
                refresh_token_expires_at=now + timedelta(minutes=15),
            )

    def test_string_representation(self) -> None:
        """Test string representation of session."""
        user_id = UserId.generate()
        session = Session.create(
            user_id=user_id,
            access_token="access-token",
            refresh_token="refresh-token",
        )

        assert f"Session({session.id}, user={user_id}" in str(session)
