"""OpenAI LLMサービス実装。

OpenAI APIを使用したLLMサービス実装。
"""

from collections.abc import AsyncIterator
from typing import Any, cast

import httpx
from openai import AsyncOpenAI, AuthenticationError, OpenAIError, RateLimitError
from openai.types.chat import ChatCompletion

from ....domain.exceptions import (
    LLMAuthenticationError,
    LLMInvalidRequestError,
    LLMModelNotAvailableError,
    LLMRateLimitError,
    LLMServiceError,
    LLMTimeoutError,
)
from ....domain.externals import LLMService
from ....domain.value_objects.llm_types import (
    LLMRequest,
    LLMResponse,
    LLMStreamChunk,
    LLMUsage,
)


class OpenAILLMService(LLMService):
    """OpenAI APIを使用したLLMサービス実装。"""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-3.5-turbo",
        max_retries: int = 3,
        timeout: float = 60.0,
        organization: str | None = None,
    ):
        """初期化する。

        Args:
            api_key: OpenAI APIキー
            model: デフォルトのモデル名
            max_retries: 最大リトライ回数
            timeout: タイムアウト秒数
            organization: OpenAI組織ID（オプション）
        """
        self._client = AsyncOpenAI(
            api_key=api_key,
            organization=organization,
            max_retries=max_retries,
            timeout=httpx.Timeout(timeout, connect=5.0),
        )
        self._model = model
        self._timeout = timeout
        self._model_info = self._get_model_info_static(model)

    def _get_model_info_static(self, model: str) -> dict[str, Any]:
        """静的なモデル情報を取得する。

        Args:
            model: モデル名

        Returns:
            モデル情報
        """
        model_configs = {
            "gpt-4": {
                "max_tokens": 8192,
                "context_size": 8192,
                "supports_streaming": True,
                "temperature_range": [0.0, 2.0],
                "price": {
                    "input_per_1k": 0.03,
                    "output_per_1k": 0.06,
                },
            },
            "gpt-4-turbo": {
                "max_tokens": 4096,
                "context_size": 128000,
                "supports_streaming": True,
                "temperature_range": [0.0, 2.0],
                "price": {
                    "input_per_1k": 0.01,
                    "output_per_1k": 0.03,
                },
            },
            "gpt-3.5-turbo": {
                "max_tokens": 4096,
                "context_size": 16385,
                "supports_streaming": True,
                "temperature_range": [0.0, 2.0],
                "price": {
                    "input_per_1k": 0.0005,
                    "output_per_1k": 0.0015,
                },
            },
        }

        config = model_configs.get(model, model_configs["gpt-3.5-turbo"])
        return {
            "name": model,
            "type": "openai",
            **config,
        }

    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """単一の応答を生成する。

        Args:
            request: LLMリクエスト

        Returns:
            LLM応答

        Raises:
            LLMAuthenticationError: 認証エラー
            LLMRateLimitError: レート制限エラー
            LLMModelNotAvailableError: モデル利用不可
            LLMInvalidRequestError: 無効なリクエスト
            LLMTimeoutError: タイムアウト
            LLMServiceError: その他のエラー
        """
        try:
            # メッセージを変換
            messages = [
                {"role": msg.role.value, "content": msg.content}
                for msg in request.messages
            ]

            # API呼び出し
            completion = await self._client.chat.completions.create(
                model=request.model or self._model,
                messages=messages,  # type: ignore
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                top_p=request.top_p,
                frequency_penalty=request.frequency_penalty,
                presence_penalty=request.presence_penalty,
                stop=request.stop,
                stream=False,
            )

            # 応答を変換（streamがFalseなのでChatCompletion型）
            response = cast(ChatCompletion, completion)
            choice = response.choices[0]
            usage = response.usage

            return LLMResponse(
                content=choice.message.content or "",
                model=response.model,
                usage=LLMUsage(
                    prompt_tokens=usage.prompt_tokens if usage else 0,
                    completion_tokens=usage.completion_tokens if usage else 0,
                    total_tokens=usage.total_tokens if usage else 0,
                ),
                finish_reason=choice.finish_reason,
                metadata={
                    "id": response.id,
                    "created": response.created,
                    "system_fingerprint": response.system_fingerprint,
                },
            )

        except AuthenticationError as e:
            raise LLMAuthenticationError("openai", str(e)) from e
        except RateLimitError as e:
            # レート制限情報を抽出
            retry_after = None
            if hasattr(e, "response") and e.response:
                retry_after = e.response.headers.get("retry-after")
                if retry_after:
                    retry_after = int(retry_after)
            raise LLMRateLimitError(str(e), retry_after) from e
        except httpx.TimeoutException as e:
            raise LLMTimeoutError(self._timeout, str(e)) from e
        except OpenAIError as e:
            if "model" in str(e).lower() and "not found" in str(e).lower():
                raise LLMModelNotAvailableError(
                    request.model or self._model, str(e)
                ) from e
            elif "invalid" in str(e).lower():
                raise LLMInvalidRequestError(str(e)) from e
            else:
                raise LLMServiceError(f"OpenAI API error: {e}") from e
        except Exception as e:
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
            LLMAuthenticationError: 認証エラー
            LLMRateLimitError: レート制限エラー
            LLMModelNotAvailableError: モデル利用不可
            LLMInvalidRequestError: 無効なリクエスト
            LLMTimeoutError: タイムアウト
            LLMServiceError: その他のエラー
        """
        try:
            # メッセージを変換
            messages = [
                {"role": msg.role.value, "content": msg.content}
                for msg in request.messages
            ]

            # ストリーミングAPI呼び出し
            stream = await self._client.chat.completions.create(
                model=request.model or self._model,
                messages=messages,  # type: ignore
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                top_p=request.top_p,
                frequency_penalty=request.frequency_penalty,
                presence_penalty=request.presence_penalty,
                stop=request.stop,
                stream=True,
            )

            # ストリーミング応答を処理
            async for chunk in stream:  # type: ignore
                if not chunk.choices:
                    continue

                choice = chunk.choices[0]
                delta = choice.delta

                # コンテンツがある場合のみチャンクを生成
                if delta.content:
                    yield LLMStreamChunk(
                        delta=delta.content,
                        model=chunk.model,
                        finish_reason=choice.finish_reason,
                        is_final=choice.finish_reason is not None,
                    )
                elif choice.finish_reason:
                    # 最後のチャンク
                    yield LLMStreamChunk(
                        delta="",
                        model=chunk.model,
                        finish_reason=choice.finish_reason,
                        is_final=True,
                    )

        except AuthenticationError as e:
            raise LLMAuthenticationError("openai", str(e)) from e
        except RateLimitError as e:
            retry_after = None
            if hasattr(e, "response") and e.response:
                retry_after = e.response.headers.get("retry-after")
                if retry_after:
                    retry_after = int(retry_after)
            raise LLMRateLimitError(str(e), retry_after) from e
        except httpx.TimeoutException as e:
            raise LLMTimeoutError(self._timeout, str(e)) from e
        except OpenAIError as e:
            if "model" in str(e).lower() and "not found" in str(e).lower():
                raise LLMModelNotAvailableError(
                    request.model or self._model, str(e)
                ) from e
            elif "invalid" in str(e).lower():
                raise LLMInvalidRequestError(str(e)) from e
            else:
                raise LLMServiceError(f"OpenAI API error: {e}") from e
        except Exception as e:
            raise LLMServiceError(f"Unexpected error: {e}") from e

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
        return self._model_info

    def supports_streaming(self) -> bool:
        """ストリーミングサポートを判定する。

        Returns:
            True（OpenAIモデルは全てサポート）
        """
        return True

    def get_max_tokens(self) -> int | None:
        """最大トークン数を取得する。

        Returns:
            最大トークン数
        """
        return cast(int, self._model_info.get("max_tokens", 4096))
