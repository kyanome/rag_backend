"""埋め込みベクトル生成サービスのファクトリー。"""

from typing import Literal

from ....domain.externals import EmbeddingService
from .mock_embedding_service import MockEmbeddingService
from .ollama_embedding_service import OllamaEmbeddingService
from .openai_embedding_service import OpenAIEmbeddingService

EmbeddingProvider = Literal["openai", "ollama", "mock"]


class EmbeddingServiceFactory:
    """埋め込みベクトル生成サービスのファクトリークラス。

    設定に応じて適切な埋め込みサービスの実装を返す。
    """

    @staticmethod
    def create(
        provider: EmbeddingProvider,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        dimensions: int = 1536,
    ) -> EmbeddingService:
        """埋め込みサービスを作成する。

        Args:
            provider: プロバイダー名（openai, ollama, mock）
            api_key: APIキー（OpenAIの場合必須）
            model: モデル名（省略時はデフォルト値を使用）
            base_url: ベースURL（Ollamaの場合のみ）
            dimensions: ベクトルの次元数（Mockの場合のみ）

        Returns:
            埋め込みサービスの実装

        Raises:
            ValueError: 不正なプロバイダー名または必須パラメータが不足している場合
        """
        if provider == "openai":
            if not api_key:
                raise ValueError("OpenAI provider requires api_key")
            return OpenAIEmbeddingService(
                api_key=api_key,
                model=model or "text-embedding-ada-002",
            )

        elif provider == "ollama":
            return OllamaEmbeddingService(
                base_url=base_url or "http://localhost:11434",
                model=model or "mxbai-embed-large",
            )

        elif provider == "mock":
            return MockEmbeddingService(
                model=model or "mock-model",
                dimensions=dimensions,
            )

        else:
            raise ValueError(
                f"Unknown embedding provider: {provider}. "
                "Supported providers: openai, ollama, mock"
            )
