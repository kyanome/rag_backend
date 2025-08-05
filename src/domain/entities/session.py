"""Session entity implementation."""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from ..value_objects import UserId


@dataclass
class Session:
    """Session entity representing a user authentication session."""

    id: str
    user_id: UserId
    access_token: str
    refresh_token: str
    access_token_expires_at: datetime
    refresh_token_expires_at: datetime
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_accessed_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    ip_address: str | None = None
    user_agent: str | None = None

    def __post_init__(self) -> None:
        """Validate session entity."""
        if not self.id:
            raise ValueError("Session ID cannot be empty")
        if not isinstance(self.user_id, UserId):
            raise TypeError("user_id must be a UserId instance")
        if not self.access_token:
            raise ValueError("Access token cannot be empty")
        if not self.refresh_token:
            raise ValueError("Refresh token cannot be empty")

        # Ensure expiration times are in the future
        now = datetime.now(UTC)
        if self.access_token_expires_at <= now:
            raise ValueError("Access token expiration must be in the future")
        if self.refresh_token_expires_at <= now:
            raise ValueError("Refresh token expiration must be in the future")
        if self.refresh_token_expires_at <= self.access_token_expires_at:
            raise ValueError("Refresh token must expire after access token")

    @classmethod
    def create(
        cls,
        user_id: UserId,
        access_token: str,
        refresh_token: str,
        access_token_ttl: timedelta = timedelta(minutes=15),
        refresh_token_ttl: timedelta = timedelta(days=30),
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> "Session":
        """Create a new session with default expiration times."""
        now = datetime.now(UTC)
        return cls(
            id=str(uuid.uuid4()),
            user_id=user_id,
            access_token=access_token,
            refresh_token=refresh_token,
            access_token_expires_at=now + access_token_ttl,
            refresh_token_expires_at=now + refresh_token_ttl,
            created_at=now,
            last_accessed_at=now,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    def is_access_token_expired(self) -> bool:
        """Check if the access token has expired."""
        return datetime.now(UTC) >= self.access_token_expires_at

    def is_refresh_token_expired(self) -> bool:
        """Check if the refresh token has expired."""
        return datetime.now(UTC) >= self.refresh_token_expires_at

    def is_expired(self) -> bool:
        """Check if the entire session has expired."""
        return self.is_refresh_token_expired()

    def can_refresh(self) -> bool:
        """Check if the session can be refreshed."""
        return not self.is_refresh_token_expired()

    def refresh(
        self,
        new_access_token: str,
        access_token_ttl: timedelta = timedelta(minutes=15),
    ) -> None:
        """Refresh the access token."""
        if not self.can_refresh():
            raise ValueError("Cannot refresh expired session")

        now = datetime.now(UTC)
        self.access_token = new_access_token
        self.access_token_expires_at = now + access_token_ttl
        self.last_accessed_at = now

    def extend_refresh_token(
        self, refresh_token_ttl: timedelta = timedelta(days=30)
    ) -> None:
        """Extend the refresh token expiration."""
        if self.is_refresh_token_expired():
            raise ValueError("Cannot extend expired refresh token")

        now = datetime.now(UTC)
        self.refresh_token_expires_at = now + refresh_token_ttl
        self.last_accessed_at = now

    def update_activity(
        self, ip_address: str | None = None, user_agent: str | None = None
    ) -> None:
        """Update session activity information."""
        self.last_accessed_at = datetime.now(UTC)
        if ip_address is not None:
            self.ip_address = ip_address
        if user_agent is not None:
            self.user_agent = user_agent

    def __str__(self) -> str:
        """Return string representation."""
        return f"Session({self.id}, user={self.user_id}, expires={self.refresh_token_expires_at})"
