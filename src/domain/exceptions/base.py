"""Base domain exceptions."""


class DomainException(Exception):
    """Base exception for all domain exceptions."""

    pass


class RepositoryError(DomainException):
    """Exception raised when a repository operation fails."""

    pass
