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
from .base import DomainException, RepositoryError
from .document_exceptions import (
    DocumentError,
    DocumentNotFoundError,
    DocumentValidationError,
    InvalidDocumentError,
)
from .embedding_exceptions import (
    EmbeddingException,
    EmbeddingGenerationError,
    EmbeddingServiceError,
    InvalidTextError,
    ModelNotAvailableError,
)

__all__ = [
    # Base
    "DomainException",
    "RepositoryError",
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
    # Embedding
    "EmbeddingException",
    "EmbeddingGenerationError",
    "EmbeddingServiceError",
    "InvalidTextError",
    "ModelNotAvailableError",
]
