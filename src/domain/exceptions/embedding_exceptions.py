"""埋め込みベクトル生成関連の例外クラス。"""

from .base import DomainException


class EmbeddingException(DomainException):
    """埋め込みベクトル生成の基底例外クラス。"""

    pass


class EmbeddingGenerationError(EmbeddingException):
    """埋め込みベクトル生成エラー。"""

    def __init__(self, message: str = "Failed to generate embedding"):
        """初期化する。

        Args:
            message: エラーメッセージ
        """
        super().__init__(message)


class InvalidTextError(EmbeddingException):
    """無効なテキストエラー。"""

    def __init__(self, message: str = "Invalid text for embedding generation"):
        """初期化する。

        Args:
            message: エラーメッセージ
        """
        super().__init__(message)


class ModelNotAvailableError(EmbeddingException):
    """モデル利用不可エラー。"""

    def __init__(self, model_name: str):
        """初期化する。

        Args:
            model_name: 利用不可なモデル名
        """
        super().__init__(f"Model '{model_name}' is not available")
        self.model_name = model_name


class EmbeddingServiceError(EmbeddingException):
    """埋め込みサービスエラー。"""

    def __init__(self, service_name: str, message: str = "Embedding service error"):
        """初期化する。

        Args:
            service_name: サービス名
            message: エラーメッセージ
        """
        super().__init__(f"{service_name}: {message}")
        self.service_name = service_name
