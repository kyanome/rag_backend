"""ドメイン層の例外定義パッケージ。"""

from .auth_exceptions import (
    AccountDisabledException,
    AuthenticationException,
    EmailNotVerifiedException,
    InsufficientPermissionsException,
    InvalidCredentialsException,
    InvalidTokenException,
    SessionExpiredException,
    UserAlreadyExistsException,
    UserNotFoundException,
)
from .base import DomainException
from .document_exceptions import (
    DocumentError,
    DocumentNotFoundError,
    DocumentValidationError,
    InvalidDocumentError,
)

__all__ = [
    # Base
    "DomainException",
    # Document
    "DocumentError",
    "DocumentNotFoundError",
    "DocumentValidationError",
    "InvalidDocumentError",
    # Auth
    "AccountDisabledException",
    "AuthenticationException",
    "EmailNotVerifiedException",
    "InsufficientPermissionsException",
    "InvalidCredentialsException",
    "InvalidTokenException",
    "SessionExpiredException",
    "UserAlreadyExistsException",
    "UserNotFoundException",
]
