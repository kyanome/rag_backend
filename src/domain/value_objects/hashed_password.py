"""HashedPassword value object implementation."""

from dataclasses import dataclass
from typing import ClassVar

from passlib.context import CryptContext


@dataclass(frozen=True)
class HashedPassword:
    """Value object representing a hashed password."""

    value: str

    # Bcrypt context for password hashing
    _pwd_context: ClassVar[CryptContext] = CryptContext(
        schemes=["bcrypt"], deprecated="auto"
    )

    def __post_init__(self) -> None:
        """Validate the hashed password."""
        if not self.value:
            raise ValueError("Hashed password cannot be empty")

        # Basic validation for bcrypt format
        if not self.value.startswith("$2"):  # bcrypt prefix
            raise ValueError("Invalid hashed password format")

    @classmethod
    def from_plain_password(cls, plain_password: str) -> "HashedPassword":
        """Create a hashed password from a plain text password."""
        if not plain_password:
            raise ValueError("Password cannot be empty")

        if len(plain_password) < 8:
            raise ValueError("Password must be at least 8 characters long")

        if len(plain_password) > 128:
            raise ValueError("Password too long")

        hashed = cls._pwd_context.hash(plain_password)
        return cls(hashed)

    def verify(self, plain_password: str) -> bool:
        """Verify a plain password against the hash."""
        if not plain_password:
            return False

        try:
            return self._pwd_context.verify(plain_password, self.value)
        except Exception:
            return False

    def __str__(self) -> str:
        """Return masked representation for security."""
        return "********"
