"""Ollama LLMサービス実装。

ローカルLLM（Ollama）を使用したLLMサービス実装。
"""

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx

from ....domain.exceptions import (
    LLMModelNotAvailableError,
    LLMServiceError,
    LLMTimeoutError,
)
from ....domain.externals import LLMService
from ....domain.value_objects.llm_types import (
    LLMRequest,
    LLMResponse,
    LLMRole,
    LLMStreamChunk,
    LLMUsage,
)


class OllamaLLMService(LLMService):
    """Ollamaを使用したローカルLLMサービス実装。"""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama2",
        timeout: float = 120.0,
    ):
        """初期化する。

        Args:
            base_url: Ollama APIのベースURL
            model: デフォルトのモデル名
            timeout: タイムアウト秒数
        """
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(timeout, connect=5.0),
        )

    async def __aenter__(self) -> "OllamaLLMService":
        """非同期コンテキストマネージャーの開始。"""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """非同期コンテキストマネージャーの終了。"""
        await self._client.aclose()

    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """単一の応答を生成する。

        Args:
            request: LLMリクエスト

        Returns:
            LLM応答

        Raises:
            LLMModelNotAvailableError: モデル利用不可
            LLMInvalidRequestError: 無効なリクエスト
            LLMTimeoutError: タイムアウト
            LLMServiceError: その他のエラー
        """
        try:
            # プロンプトを構築
            prompt = self._build_prompt(request)

            # Ollama API呼び出し
            response = await self._client.post(
                "/api/generate",
                json={
                    "model": request.model or self._model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": request.temperature,
                        "top_p": request.top_p,
                        "stop": request.stop,
                    },
                },
            )

            if response.status_code != 200:
                error_text = response.text
                if "model" in error_text.lower() and "not found" in error_text.lower():
                    raise LLMModelNotAvailableError(
                        request.model or self._model,
                        f"Ollama model not found: {error_text}",
                    )
                else:
                    raise LLMServiceError(
                        f"Ollama API error: {response.status_code} - {error_text}"
                    )

            data = response.json()

            # トークン数の推定（文字数ベース）
            prompt_tokens = len(prompt) // 4
            completion_tokens = len(data.get("response", "")) // 4

            return LLMResponse(
                content=data.get("response", ""),
                model=data.get("model", request.model or self._model),
                usage=LLMUsage(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens,
                ),
                finish_reason="stop" if data.get("done") else "length",
                metadata={
                    "context": data.get("context"),
                    "eval_count": data.get("eval_count"),
                    "eval_duration": data.get("eval_duration"),
                },
            )

        except httpx.TimeoutException as e:
            raise LLMTimeoutError(self._timeout, str(e)) from e
        except httpx.HTTPError as e:
            raise LLMServiceError(f"Ollama connection error: {e}") from e
        except json.JSONDecodeError as e:
            raise LLMServiceError(f"Invalid response from Ollama: {e}") from e
        except Exception as e:
            if isinstance(e, LLMModelNotAvailableError | LLMServiceError):
                raise
            raise LLMServiceError(f"Unexpected error: {e}") from e

    async def stream_response(
        self, request: LLMRequest
    ) -> AsyncIterator[LLMStreamChunk]:
        """ストリーミング応答を生成する。

        Args:
            request: LLMリクエスト

        Yields:
            ストリーミングチャンク

        Raises:
            LLMModelNotAvailableError: モデル利用不可
            LLMInvalidRequestError: 無効なリクエスト
            LLMTimeoutError: タイムアウト
            LLMServiceError: その他のエラー
        """
        try:
            # プロンプトを構築
            prompt = self._build_prompt(request)

            # ストリーミングAPI呼び出し
            async with self._client.stream(
                "POST",
                "/api/generate",
                json={
                    "model": request.model or self._model,
                    "prompt": prompt,
                    "stream": True,
                    "options": {
                        "temperature": request.temperature,
                        "top_p": request.top_p,
                        "stop": request.stop,
                    },
                },
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    error_str = error_text.decode("utf-8")
                    if (
                        "model" in error_str.lower()
                        and "not found" in error_str.lower()
                    ):
                        raise LLMModelNotAvailableError(
                            request.model or self._model,
                            f"Ollama model not found: {error_str}",
                        )
                    else:
                        raise LLMServiceError(
                            f"Ollama API error: {response.status_code} - {error_str}"
                        )

                # ストリーミング応答を処理
                async for line in response.aiter_lines():
                    if not line:
                        continue

                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    # チャンクを生成
                    is_done = data.get("done", False)
                    response_text = data.get("response", "")

                    if response_text or is_done:
                        yield LLMStreamChunk(
                            delta=response_text,
                            model=data.get("model", request.model or self._model),
                            finish_reason="stop" if is_done else None,
                            is_final=is_done,
                        )

        except httpx.TimeoutException as e:
            raise LLMTimeoutError(self._timeout, str(e)) from e
        except httpx.HTTPError as e:
            raise LLMServiceError(f"Ollama connection error: {e}") from e
        except Exception as e:
            if isinstance(e, LLMModelNotAvailableError | LLMServiceError):
                raise
            raise LLMServiceError(f"Unexpected error: {e}") from e

    def _build_prompt(self, request: LLMRequest) -> str:
        """リクエストからプロンプトを構築する。

        Args:
            request: LLMリクエスト

        Returns:
            プロンプト文字列
        """
        prompt_parts = []

        for message in request.messages:
            if message.role == LLMRole.SYSTEM:
                prompt_parts.append(f"System: {message.content}")
            elif message.role == LLMRole.USER:
                prompt_parts.append(f"User: {message.content}")
            elif message.role == LLMRole.ASSISTANT:
                prompt_parts.append(f"Assistant: {message.content}")

        # 最後にAssistantのプロンプトを追加
        prompt_parts.append("Assistant:")

        return "\n\n".join(prompt_parts)

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
        # Ollamaのモデル情報（一般的な値）
        return {
            "name": self._model,
            "type": "ollama",
            "max_tokens": 4096,
            "context_size": 4096,
            "supports_streaming": True,
            "temperature_range": [0.0, 2.0],
            "price": {
                "input_per_1k": 0.0,  # ローカルなので無料
                "output_per_1k": 0.0,
            },
        }

    def supports_streaming(self) -> bool:
        """ストリーミングサポートを判定する。

        Returns:
            True（Ollamaは全てサポート）
        """
        return True

    def get_max_tokens(self) -> int | None:
        """最大トークン数を取得する。

        Returns:
            4096（一般的な値）
        """
        return 4096

    async def list_models(self) -> list[str]:
        """利用可能なモデル一覧を取得する。

        Returns:
            モデル名のリスト

        Raises:
            LLMServiceError: API呼び出しエラー
        """
        try:
            response = await self._client.get("/api/tags")
            if response.status_code != 200:
                raise LLMServiceError(
                    f"Failed to list models: {response.status_code} - {response.text}"
                )

            data = response.json()
            models = data.get("models", [])
            return [model.get("name", "") for model in models if model.get("name")]

        except httpx.HTTPError as e:
            raise LLMServiceError(f"Ollama connection error: {e}") from e
        except Exception as e:
            if isinstance(e, LLMServiceError):
                raise
            raise LLMServiceError(f"Failed to list models: {e}") from e

    async def pull_model(self, model_name: str) -> None:
        """モデルをダウンロードする。

        Args:
            model_name: ダウンロードするモデル名

        Raises:
            LLMServiceError: ダウンロードエラー
        """
        try:
            response = await self._client.post(
                "/api/pull",
                json={"name": model_name},
                timeout=None,  # ダウンロードは時間がかかるため
            )

            if response.status_code != 200:
                raise LLMServiceError(
                    f"Failed to pull model: {response.status_code} - {response.text}"
                )

        except httpx.HTTPError as e:
            raise LLMServiceError(f"Ollama connection error: {e}") from e
        except Exception as e:
            if isinstance(e, LLMServiceError):
                raise
            raise LLMServiceError(f"Failed to pull model: {e}") from e
