"""Mock LLMサービス実装。

テスト用のモックLLMサービス実装。
"""

import asyncio
from collections.abc import AsyncIterator
from typing import Any

from ....domain.exceptions import LLMInvalidRequestError, LLMRateLimitError
from ....domain.externals import LLMService
from ....domain.value_objects.llm_types import (
    LLMRequest,
    LLMResponse,
    LLMStreamChunk,
    LLMUsage,
)


class MockLLMService(LLMService):
    """Mock LLMサービス実装。

    テストおよび開発環境で使用するモック実装。
    """

    def __init__(
        self,
        model: str = "mock-model",
        default_response: str = "This is a mock response.",
        stream_delay: float = 0.01,
        simulate_rate_limit: bool = False,
        simulate_error: bool = False,
    ):
        """初期化する。

        Args:
            model: モデル名
            default_response: デフォルトの応答テキスト
            stream_delay: ストリーミング時のチャンク間遅延（秒）
            simulate_rate_limit: レート制限をシミュレートするか
            simulate_error: エラーをシミュレートするか
        """
        self._model = model
        self._default_response = default_response
        self._stream_delay = stream_delay
        self._simulate_rate_limit = simulate_rate_limit
        self._simulate_error = simulate_error
        self._call_count = 0

    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """単一の応答を生成する。

        Args:
            request: LLMリクエスト

        Returns:
            モック応答

        Raises:
            LLMRateLimitError: レート制限シミュレーション時
            LLMInvalidRequestError: エラーシミュレーション時
        """
        self._call_count += 1

        # エラーシミュレーション
        if self._simulate_rate_limit and self._call_count % 3 == 0:
            raise LLMRateLimitError("Mock rate limit exceeded", retry_after=5)

        if self._simulate_error:
            raise LLMInvalidRequestError("Mock error", {"error": "simulated"})

        # リクエストバリデーション
        if not request.messages:
            raise LLMInvalidRequestError("No messages provided")

        # 簡単な応答生成ロジック
        last_message = request.messages[-1].content
        if "hello" in last_message.lower():
            response_text = "Hello! How can I help you today?"
        elif "?" in last_message:
            response_text = f"That's an interesting question about: {last_message[:50]}"
        else:
            response_text = self._default_response

        # トークン数の簡易計算（文字数ベース）
        prompt_tokens = sum(len(msg.content) for msg in request.messages) // 4
        completion_tokens = len(response_text) // 4

        return LLMResponse(
            content=response_text,
            model=request.model or self._model,
            usage=LLMUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
            finish_reason="stop",
            metadata={
                "mock": True,
                "call_count": self._call_count,
            },
        )

    async def stream_response(
        self, request: LLMRequest
    ) -> AsyncIterator[LLMStreamChunk]:
        """ストリーミング応答を生成する。

        Args:
            request: LLMリクエスト

        Yields:
            ストリーミングチャンク

        Raises:
            LLMRateLimitError: レート制限シミュレーション時
            LLMInvalidRequestError: エラーシミュレーション時
        """
        # 通常の応答を生成
        response = await self.generate_response(request)

        # 応答をチャンクに分割
        words = response.content.split()
        total_chunks = len(words)

        for i, word in enumerate(words):
            # チャンクを生成
            is_last = i == total_chunks - 1
            chunk_text = word if is_last else word + " "

            yield LLMStreamChunk(
                delta=chunk_text,
                model=response.model,
                finish_reason="stop" if is_last else None,
                is_final=is_last,
            )

            # 遅延をシミュレート
            if not is_last:
                await asyncio.sleep(self._stream_delay)

    def get_model_name(self) -> str:
        """モデル名を取得する。

        Returns:
            モデル名
        """
        return self._model

    def get_model_info(self) -> dict[str, Any]:
        """モデル情報を取得する。

        Returns:
            モデル情報
        """
        return {
            "name": self._model,
            "type": "mock",
            "max_tokens": 4096,
            "context_size": 8192,
            "supports_streaming": True,
            "temperature_range": [0.0, 2.0],
            "price": {
                "input_per_1k": 0.0,
                "output_per_1k": 0.0,
            },
        }

    def supports_streaming(self) -> bool:
        """ストリーミングサポートを判定する。

        Returns:
            True（常にサポート）
        """
        return True

    def get_max_tokens(self) -> int | None:
        """最大トークン数を取得する。

        Returns:
            4096
        """
        return 4096

    def set_response(self, response: str) -> None:
        """モック応答を設定する。

        Args:
            response: 設定する応答テキスト
        """
        self._default_response = response

    def enable_rate_limit_simulation(self, enabled: bool = True) -> None:
        """レート制限シミュレーションを有効化する。

        Args:
            enabled: 有効化フラグ
        """
        self._simulate_rate_limit = enabled

    def enable_error_simulation(self, enabled: bool = True) -> None:
        """エラーシミュレーションを有効化する。

        Args:
            enabled: 有効化フラグ
        """
        self._simulate_error = enabled

    def reset_call_count(self) -> None:
        """呼び出し回数をリセットする。"""
        self._call_count = 0
