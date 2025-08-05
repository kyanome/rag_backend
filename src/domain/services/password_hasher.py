"""Password hasher domain service."""

from ..value_objects import HashedPassword


class PasswordHasher:
    """Domain service for password hashing and verification."""

    @staticmethod
    def hash_password(plain_password: str) -> HashedPassword:
        """Hash a plain text password.

        Args:
            plain_password: The plain text password to hash

        Returns:
            A HashedPassword value object

        Raises:
            ValueError: If the password is invalid
        """
        return HashedPassword.from_plain_password(plain_password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: HashedPassword) -> bool:
        """Verify a plain password against a hashed password.

        Args:
            plain_password: The plain text password to verify
            hashed_password: The hashed password to verify against

        Returns:
            True if the password matches, False otherwise
        """
        return hashed_password.verify(plain_password)
