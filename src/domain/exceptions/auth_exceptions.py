"""Authentication and authorization related exceptions."""

from .base import DomainException


class AuthenticationException(DomainException):
    """Base exception for authentication errors."""

    pass


class UserNotFoundException(AuthenticationException):
    """Exception raised when a user is not found."""

    def __init__(self, message: str = "User not found") -> None:
        """Initialize the exception.

        Args:
            message: The error message
        """
        super().__init__(message)


class InvalidCredentialsException(AuthenticationException):
    """Exception raised when credentials are invalid."""

    def __init__(self, message: str = "Invalid email or password") -> None:
        """Initialize the exception.

        Args:
            message: The error message
        """
        super().__init__(message)


class SessionExpiredException(AuthenticationException):
    """Exception raised when a session has expired."""

    def __init__(self, message: str = "Session has expired") -> None:
        """Initialize the exception.

        Args:
            message: The error message
        """
        super().__init__(message)


class InvalidTokenException(AuthenticationException):
    """Exception raised when a token is invalid."""

    def __init__(self, message: str = "Invalid token") -> None:
        """Initialize the exception.

        Args:
            message: The error message
        """
        super().__init__(message)


class UserAlreadyExistsException(DomainException):
    """Exception raised when attempting to create a user that already exists."""

    def __init__(
        self,
        email: str | None = None,
        message: str | None = None,
    ) -> None:
        """Initialize the exception.

        Args:
            email: The email address that already exists
            message: Custom error message
        """
        if message is None:
            message = (
                f"User with email {email} already exists"
                if email
                else "User already exists"
            )
        super().__init__(message)
        self.email = email


class InsufficientPermissionsException(DomainException):
    """Exception raised when a user lacks required permissions."""

    def __init__(
        self,
        required_permission: str | None = None,
        message: str | None = None,
    ) -> None:
        """Initialize the exception.

        Args:
            required_permission: The permission that was required
            message: Custom error message
        """
        if message is None:
            message = (
                f"Insufficient permissions. Required: {required_permission}"
                if required_permission
                else "Insufficient permissions"
            )
        super().__init__(message)
        self.required_permission = required_permission


class AccountDisabledException(AuthenticationException):
    """Exception raised when attempting to authenticate with a disabled account."""

    def __init__(self, message: str = "Account is disabled") -> None:
        """Initialize the exception.

        Args:
            message: The error message
        """
        super().__init__(message)


class EmailNotVerifiedException(AuthenticationException):
    """Exception raised when email verification is required but not completed."""

    def __init__(self, message: str = "Email address not verified") -> None:
        """Initialize the exception.

        Args:
            message: The error message
        """
        super().__init__(message)
