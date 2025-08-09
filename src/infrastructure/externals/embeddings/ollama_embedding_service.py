"""Ollamaを使用したローカル埋め込みベクトル生成サービス。"""

import httpx

from ....domain.exceptions import (
    EmbeddingGenerationError,
    EmbeddingServiceError,
    InvalidTextError,
    ModelNotAvailableError,
)
from ....domain.externals import EmbeddingResult, EmbeddingService


class OllamaEmbeddingService(EmbeddingService):
    """Ollamaを使用したローカル埋め込みベクトル生成サービス。

    ローカル開発環境用のOllama APIを使用して埋め込みベクトルを生成する。
    """

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "mxbai-embed-large",
        timeout: float = 30.0,
    ):
        """初期化する。

        Args:
            base_url: Ollama APIのベースURL
            model: 使用するモデル名
            timeout: タイムアウト秒数
        """
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout
        self._dimensions = 1024  # mxbai-embed-largeのデフォルト次元数

    async def _check_model_availability(self) -> bool:
        """モデルが利用可能かチェックする。

        Returns:
            モデルが利用可能な場合True
        """
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(f"{self._base_url}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    models = [model["name"] for model in data.get("models", [])]
                    return self._model in models or f"{self._model}:latest" in models
                return False
        except Exception:
            return False

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

        # モデルの利用可能性をチェック
        if not await self._check_model_availability():
            raise ModelNotAvailableError(self._model)

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    f"{self._base_url}/api/embeddings",
                    json={
                        "model": self._model,
                        "prompt": text,
                    },
                )

                if response.status_code != 200:
                    raise EmbeddingServiceError(
                        "Ollama",
                        f"API returned status {response.status_code}: {response.text}",
                    )

                data = response.json()
                embedding = data.get("embedding", [])

                if not embedding:
                    raise EmbeddingGenerationError("No embedding returned from Ollama")

                return EmbeddingResult(
                    embedding=embedding,
                    model=self._model,
                    dimensions=len(embedding),
                )

        except (ModelNotAvailableError, InvalidTextError, EmbeddingServiceError):
            raise
        except httpx.ConnectError as e:
            raise EmbeddingServiceError(
                "Ollama",
                f"Failed to connect to Ollama at {self._base_url}. "
                "Please ensure Ollama is running.",
            ) from e
        except Exception as e:
            raise EmbeddingGenerationError(
                f"Failed to generate embedding: {str(e)}"
            ) from e

    async def generate_batch_embeddings(
        self, texts: list[str]
    ) -> list[EmbeddingResult]:
        """複数のテキストから埋め込みベクトルをバッチ生成する。

        Ollamaは現在バッチ処理をサポートしていないため、
        順次処理を行う。

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

        # Ollamaはバッチ処理をサポートしていないため、順次処理
        results: list[EmbeddingResult] = []
        for text in valid_texts:
            result = await self.generate_embedding(text)
            results.append(result)

        return results

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
