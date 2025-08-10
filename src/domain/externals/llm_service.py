"""LLMサービスインターフェース。

Large Language Model（LLM）サービスの抽象インターフェースを定義する。
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

from ..value_objects.llm_types import LLMRequest, LLMResponse, LLMStreamChunk


class LLMService(ABC):
    """LLMサービスの抽象インターフェース。

    テキスト生成のためのLLMサービスを抽象化する。
    具体的な実装はインフラストラクチャ層で行う。
    """

    @abstractmethod
    async def generate_response(
        self,
        request: LLMRequest,
    ) -> LLMResponse:
        """単一の応答を生成する。

        Args:
            request: LLMリクエスト

        Returns:
            LLM応答

        Raises:
            LLMServiceError: LLMサービスでエラーが発生した場合
            LLMModelNotAvailableError: モデルが利用できない場合
            LLMRateLimitError: レート制限に達した場合
            LLMInvalidRequestError: リクエストが無効な場合
        """
        pass

    @abstractmethod
    def stream_response(
        self,
        request: LLMRequest,
    ) -> AsyncIterator[LLMStreamChunk]:
        """ストリーミング応答を生成する。

        Args:
            request: LLMリクエスト（streamフラグは自動的にTrueに設定）

        Yields:
            ストリーミング応答のチャンク

        Raises:
            LLMServiceError: LLMサービスでエラーが発生した場合
            LLMModelNotAvailableError: モデルが利用できない場合
            LLMRateLimitError: レート制限に達した場合
            LLMInvalidRequestError: リクエストが無効な場合
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """使用しているモデル名を取得する。

        Returns:
            モデル名
        """
        pass

    @abstractmethod
    def get_model_info(self) -> dict[str, Any]:
        """モデル情報を取得する。

        Returns:
            モデル情報の辞書（コンテキストサイズ、価格情報など）
        """
        pass

    @abstractmethod
    def supports_streaming(self) -> bool:
        """ストリーミングをサポートしているかどうかを判定する。

        Returns:
            ストリーミングサポートの可否
        """
        pass

    @abstractmethod
    def get_max_tokens(self) -> int | None:
        """モデルの最大トークン数を取得する。

        Returns:
            最大トークン数（制限がない場合はNone）
        """
        pass

    async def generate_with_retry(
        self,
        request: LLMRequest,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> LLMResponse:
        """リトライ機能付きで応答を生成する。

        Args:
            request: LLMリクエスト
            max_retries: 最大リトライ回数
            retry_delay: リトライ間の遅延秒数

        Returns:
            LLM応答

        Raises:
            LLMServiceError: 全てのリトライが失敗した場合
        """
        import asyncio

        from ..exceptions import LLMRateLimitError, LLMServiceError

        last_error: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                return await self.generate_response(request)
            except LLMRateLimitError as e:
                last_error = e
                if attempt < max_retries:
                    await asyncio.sleep(retry_delay * (2**attempt))
                    continue
                raise
            except LLMServiceError as e:
                last_error = e
                if attempt < max_retries and "timeout" in str(e).lower():
                    await asyncio.sleep(retry_delay)
                    continue
                raise
            except Exception as e:
                last_error = e
                raise LLMServiceError(f"Unexpected error: {e}") from e

        if last_error:
            raise last_error
        raise LLMServiceError("Failed after all retries")
