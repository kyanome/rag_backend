"""Email value object implementation."""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Email:
    """Value object representing an email address."""

    value: str

    # RFC 5322 compliant email regex pattern
    EMAIL_PATTERN = re.compile(
        r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9]"
        r"(?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9]"
        r"(?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
    )

    def __post_init__(self) -> None:
        """Validate the email format."""
        if not self.value:
            raise ValueError("Email cannot be empty")

        # Normalize email to lowercase
        object.__setattr__(self, "value", self.value.lower().strip())

        if not self.EMAIL_PATTERN.match(self.value):
            raise ValueError(f"Invalid email format: {self.value}")

        if len(self.value) > 254:  # RFC 5321
            raise ValueError("Email address too long")

    def __str__(self) -> str:
        """Return string representation."""
        return self.value
