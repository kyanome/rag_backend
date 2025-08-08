"""Password hasher implementation."""

from ...domain.services import PasswordHasher
from ...domain.value_objects import HashedPassword


class PasswordHasherImpl(PasswordHasher):
    """Password hasher implementation using HashedPassword value object."""

    def hash(self, plain_password: str) -> str:
        """Hash a plain text password.

        Args:
            plain_password: The plain text password to hash

        Returns:
            The hashed password string

        Raises:
            ValueError: If password is invalid
        """
        hashed = HashedPassword.from_plain_password(plain_password)
        return hashed.value

    def verify(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a plain password against a hash.

        Args:
            plain_password: The plain text password to verify
            hashed_password: The hashed password to verify against

        Returns:
            True if the password matches, False otherwise
        """
        try:
            hashed = HashedPassword(hashed_password)
            return hashed.verify(plain_password)
        except ValueError:
            return False


def get_password_hasher() -> PasswordHasher:
    """Get password hasher instance.

    Returns:
        Password hasher instance
    """
    return PasswordHasherImpl()
