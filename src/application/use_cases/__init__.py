"""Application use cases."""

from .delete_document import DeleteDocumentInput, DeleteDocumentUseCase
from .get_document import GetDocumentInput, GetDocumentOutput, GetDocumentUseCase
from .get_document_list import (
    GetDocumentListInput,
    GetDocumentListOutput,
    GetDocumentListUseCase,
)
from .update_document import (
    UpdateDocumentInput,
    UpdateDocumentOutput,
    UpdateDocumentUseCase,
)
from .upload_document import (
    UploadDocumentInput,
    UploadDocumentOutput,
    UploadDocumentUseCase,
)

__all__ = [
    "UploadDocumentInput",
    "UploadDocumentOutput",
    "UploadDocumentUseCase",
    "GetDocumentListInput",
    "GetDocumentListOutput",
    "GetDocumentListUseCase",
    "GetDocumentInput",
    "GetDocumentOutput",
    "GetDocumentUseCase",
    "UpdateDocumentInput",
    "UpdateDocumentOutput",
    "UpdateDocumentUseCase",
    "DeleteDocumentInput",
    "DeleteDocumentUseCase",
]
