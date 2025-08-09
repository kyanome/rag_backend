"""OpenAI APIを使用した埋め込みベクトル生成サービス。"""

import httpx
from openai import AsyncOpenAI, OpenAIError

from ....domain.exceptions import (
    EmbeddingGenerationError,
    InvalidTextError,
    ModelNotAvailableError,
)
from ....domain.externals import EmbeddingResult, EmbeddingService


class OpenAIEmbeddingService(EmbeddingService):
    """OpenAI APIを使用した埋め込みベクトル生成サービス。"""

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-ada-002",
        max_retries: int = 3,
        timeout: float = 30.0,
    ):
        """初期化する。

        Args:
            api_key: OpenAI APIキー
            model: 使用するモデル名
            max_retries: 最大リトライ回数
            timeout: タイムアウト秒数
        """
        self._client = AsyncOpenAI(
            api_key=api_key,
            max_retries=max_retries,
            timeout=httpx.Timeout(timeout, connect=5.0),
        )
        self._model = model
        self._dimensions = self._get_model_dimensions(model)

    def _get_model_dimensions(self, model: str) -> int:
        """モデルの次元数を取得する。

        Args:
            model: モデル名

        Returns:
            次元数
        """
        dimensions_map = {
            "text-embedding-ada-002": 1536,
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
        }
        return dimensions_map.get(model, 1536)

    async def generate_embedding(self, text: str) -> EmbeddingResult:
        """単一のテキストから埋め込みベクトルを生成する。

        Args:
            text: 埋め込みを生成するテキスト

        Returns:
            埋め込みベクトル生成結果

        Raises:
            InvalidTextError: テキストが空または無効な場合
            ModelNotAvailableError: モデルが利用できない場合
            EmbeddingGenerationError: 埋め込み生成に失敗した場合
        """
        if not text or not text.strip():
            raise InvalidTextError("Text cannot be empty")

        try:
            response = await self._client.embeddings.create(
                model=self._model,
                input=text,
            )

            embedding = response.data[0].embedding

            return EmbeddingResult(
                embedding=embedding,
                model=self._model,
                dimensions=len(embedding),
            )

        except OpenAIError as e:
            if "model" in str(e).lower():
                raise ModelNotAvailableError(self._model) from e
            raise EmbeddingGenerationError(f"OpenAI API error: {str(e)}") from e
        except Exception as e:
            raise EmbeddingGenerationError(
                f"Failed to generate embedding: {str(e)}"
            ) from e

    async def generate_batch_embeddings(
        self, texts: list[str]
    ) -> list[EmbeddingResult]:
        """複数のテキストから埋め込みベクトルをバッチ生成する。

        Args:
            texts: 埋め込みを生成するテキストのリスト

        Returns:
            埋め込みベクトル生成結果のリスト

        Raises:
            InvalidTextError: テキストリストが空または無効な場合
            ModelNotAvailableError: モデルが利用できない場合
            EmbeddingGenerationError: 埋め込み生成に失敗した場合
        """
        if not texts:
            raise InvalidTextError("Text list cannot be empty")

        # 空のテキストをフィルタリング
        valid_texts = [text for text in texts if text and text.strip()]
        if not valid_texts:
            raise InvalidTextError("All texts are empty")

        # OpenAI APIは最大100件までバッチ処理可能
        batch_size = 100
        results: list[EmbeddingResult] = []

        try:
            for i in range(0, len(valid_texts), batch_size):
                batch = valid_texts[i : i + batch_size]

                response = await self._client.embeddings.create(
                    model=self._model,
                    input=batch,
                )

                for data in response.data:
                    results.append(
                        EmbeddingResult(
                            embedding=data.embedding,
                            model=self._model,
                            dimensions=len(data.embedding),
                        )
                    )

            return results

        except OpenAIError as e:
            if "model" in str(e).lower():
                raise ModelNotAvailableError(self._model) from e
            raise EmbeddingGenerationError(f"OpenAI API error: {str(e)}") from e
        except Exception as e:
            raise EmbeddingGenerationError(
                f"Failed to generate batch embeddings: {str(e)}"
            ) from e

    def get_model_name(self) -> str:
        """使用しているモデル名を取得する。

        Returns:
            モデル名
        """
        return self._model

    def get_dimensions(self) -> int:
        """埋め込みベクトルの次元数を取得する。

        Returns:
            次元数
        """
        return self._dimensions

    async def close(self) -> None:
        """クライアントをクローズする。"""
        await self._client.close()
