"""UserId value object implementation."""

import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class UserId:
    """Value object representing a user identifier."""

    value: str

    def __post_init__(self) -> None:
        """Validate the user ID format."""
        if not self.value:
            raise ValueError("User ID cannot be empty")

        try:
            uuid.UUID(self.value)
        except ValueError as e:
            raise ValueError(f"Invalid user ID format: {self.value}") from e

    @classmethod
    def generate(cls) -> "UserId":
        """Generate a new user ID."""
        return cls(str(uuid.uuid4()))

    def __str__(self) -> str:
        """Return string representation."""
        return self.value
