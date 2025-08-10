"""LLMサービス関連の例外定義。

Large Language Model（LLM）サービスで発生する例外を定義する。
"""

from .base import DomainException


class LLMServiceError(DomainException):
    """LLMサービスエラーの基底クラス。"""

    pass


class LLMModelNotAvailableError(LLMServiceError):
    """LLMモデルが利用できない場合の例外。"""

    def __init__(self, model: str, message: str | None = None):
        """初期化する。

        Args:
            model: モデル名
            message: エラーメッセージ
        """
        self.model = model
        super().__init__(message or f"Model '{model}' is not available")


class LLMRateLimitError(LLMServiceError):
    """レート制限に達した場合の例外。"""

    def __init__(
        self,
        message: str | None = None,
        retry_after: int | None = None,
    ):
        """初期化する。

        Args:
            message: エラーメッセージ
            retry_after: リトライまでの秒数
        """
        self.retry_after = retry_after
        super().__init__(
            message or f"Rate limit exceeded. Retry after {retry_after} seconds"
            if retry_after
            else "Rate limit exceeded"
        )


class LLMInvalidRequestError(LLMServiceError):
    """無効なリクエストの例外。"""

    def __init__(self, message: str, details: dict | None = None):
        """初期化する。

        Args:
            message: エラーメッセージ
            details: エラーの詳細情報
        """
        self.details = details or {}
        super().__init__(message)


class LLMTimeoutError(LLMServiceError):
    """タイムアウトエラー。"""

    def __init__(self, timeout: float, message: str | None = None):
        """初期化する。

        Args:
            timeout: タイムアウト秒数
            message: エラーメッセージ
        """
        self.timeout = timeout
        super().__init__(message or f"Request timed out after {timeout} seconds")


class LLMAuthenticationError(LLMServiceError):
    """認証エラー。"""

    def __init__(self, provider: str, message: str | None = None):
        """初期化する。

        Args:
            provider: プロバイダー名
            message: エラーメッセージ
        """
        self.provider = provider
        super().__init__(message or f"Authentication failed for provider '{provider}'")
