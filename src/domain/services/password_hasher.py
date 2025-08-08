"""Password hasher domain service."""

from abc import ABC, abstractmethod

from ..value_objects import HashedPassword


class PasswordHasher(ABC):
    """Abstract base class for password hashing and verification."""

    @abstractmethod
    def hash(self, plain_password: str) -> str:
        """Hash a plain text password.

        Args:
            plain_password: The plain text password to hash

        Returns:
            The hashed password string

        Raises:
            ValueError: If the password is invalid
        """
        pass

    @abstractmethod
    def verify(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a plain password against a hashed password.

        Args:
            plain_password: The plain text password to verify
            hashed_password: The hashed password to verify against

        Returns:
            True if the password matches, False otherwise
        """
        pass

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
