"""ドメイン層の例外定義パッケージ。"""

from .document_exceptions import (
    DocumentError,
    DocumentNotFoundError,
    DocumentValidationError,
    InvalidDocumentError,
)

__all__ = [
    "DocumentError",
    "DocumentNotFoundError",
    "DocumentValidationError",
    "InvalidDocumentError",
]
