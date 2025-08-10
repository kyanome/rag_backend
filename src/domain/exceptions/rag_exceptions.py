"""RAG処理に関する例外。

RAG（Retrieval-Augmented Generation）処理で発生する例外を定義する。
"""

from .base import DomainException


class RAGException(DomainException):
    """RAG処理の基底例外。"""

    pass


class RAGServiceError(RAGException):
    """RAGサービスでエラーが発生した場合の例外。"""

    pass


class RAGProcessingError(RAGException):
    """RAG処理中にエラーが発生した場合の例外。"""

    pass


class RAGContextBuildError(RAGException):
    """RAGコンテキスト構築中にエラーが発生した場合の例外。"""

    pass


class RAGAnswerGenerationError(RAGException):
    """RAG回答生成中にエラーが発生した場合の例外。"""

    pass


class InsufficientContextError(RAGException):
    """コンテキストが不十分な場合の例外。"""

    pass


class InvalidRAGQueryError(RAGException):
    """無効なRAGクエリの場合の例外。"""

    pass
