"""User entity implementation."""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from ..value_objects import Email, HashedPassword, UserId, UserRole


@dataclass
class User:
    """User entity representing a system user."""

    id: UserId
    email: Email
    hashed_password: HashedPassword
    name: str
    role: UserRole
    is_active: bool = True
    is_email_verified: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    last_login_at: datetime | None = None

    def __post_init__(self) -> None:
        """Validate user entity."""
        if not isinstance(self.id, UserId):
            raise TypeError("id must be a UserId instance")
        if not isinstance(self.email, Email):
            raise TypeError("email must be an Email instance")
        if not isinstance(self.hashed_password, HashedPassword):
            raise TypeError("hashed_password must be a HashedPassword instance")
        if not isinstance(self.role, UserRole):
            raise TypeError("role must be a UserRole instance")

    @classmethod
    def create(
        cls,
        email: Email,
        hashed_password: HashedPassword,
        name: str,
        role: UserRole,
    ) -> "User":
        """Create a new user with generated ID."""
        return cls(
            id=UserId(str(uuid.uuid4())),
            email=email,
            hashed_password=hashed_password,
            name=name,
            role=role,
            is_active=True,
            is_email_verified=False,
        )

    def verify_password(self, plain_password: str) -> bool:
        """Verify a plain password against the user's hashed password."""
        return self.hashed_password.verify(plain_password)

    def update_password(self, new_hashed_password: HashedPassword) -> None:
        """Update the user's password."""
        if not isinstance(new_hashed_password, HashedPassword):
            raise TypeError("new_hashed_password must be a HashedPassword instance")

        self.hashed_password = new_hashed_password
        self.updated_at = datetime.now(UTC)

    def update_email(self, new_email: Email) -> None:
        """Update the user's email address."""
        if not isinstance(new_email, Email):
            raise TypeError("new_email must be an Email instance")

        self.email = new_email
        self.is_email_verified = False
        self.updated_at = datetime.now(UTC)

    def update_role(self, new_role: UserRole) -> None:
        """Update the user's role."""
        if not isinstance(new_role, UserRole):
            raise TypeError("new_role must be a UserRole instance")

        self.role = new_role
        self.updated_at = datetime.now(UTC)

    def activate(self) -> None:
        """Activate the user account."""
        self.is_active = True
        self.updated_at = datetime.now(UTC)

    def deactivate(self) -> None:
        """Deactivate the user account."""
        self.is_active = False
        self.updated_at = datetime.now(UTC)

    def verify_email(self) -> None:
        """Mark the user's email as verified."""
        self.is_email_verified = True
        self.updated_at = datetime.now(UTC)

    def record_login(self) -> None:
        """Record the user's login timestamp."""
        self.last_login_at = datetime.now(UTC)

    def update_last_login(self) -> None:
        """Update the user's last login timestamp."""
        self.last_login_at = datetime.now(UTC)

    def can_login(self) -> bool:
        """Check if the user can login."""
        return self.is_active

    def __str__(self) -> str:
        """Return string representation."""
        return f"User({self.id}, {self.email}, role={self.role})"
