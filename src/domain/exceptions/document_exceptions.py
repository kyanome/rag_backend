"""文書関連の例外定義。"""


class DocumentError(Exception):
    """文書関連の基底例外クラス。"""

    pass


class DocumentNotFoundError(DocumentError):
    """文書が見つからない場合の例外。"""

    def __init__(self, document_id: str) -> None:
        super().__init__(f"Document with id '{document_id}' not found")
        self.document_id = document_id


class InvalidDocumentError(DocumentError):
    """無効な文書データの場合の例外。"""

    pass


class DocumentValidationError(DocumentError):
    """文書のバリデーションエラー。"""

    def __init__(self, field: str, message: str) -> None:
        super().__init__(f"Validation error for field '{field}': {message}")
        self.field = field
        self.message = message
