"""埋め込みベクトル生成インターフェース。

外部サービスによる埋め込みベクトル生成を抽象化する。
"""

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field


class EmbeddingResult(BaseModel):
    """埋め込みベクトル生成結果を表す値オブジェクト。

    Attributes:
        embedding: 埋め込みベクトル
        model: 使用されたモデル名
        dimensions: ベクトルの次元数
    """

    embedding: list[float] = Field(..., description="埋め込みベクトル")
    model: str = Field(..., description="使用されたモデル名")
    dimensions: int = Field(..., description="ベクトルの次元数")

    model_config = {"frozen": True}

    @property
    def is_valid(self) -> bool:
        """埋め込みベクトルが有効かどうかを判定する。"""
        return (
            len(self.embedding) > 0
            and len(self.embedding) == self.dimensions
            and all(isinstance(x, float) for x in self.embedding)
        )


class EmbeddingService(ABC):
    """埋め込みベクトル生成インターフェース。

    テキストから埋め込みベクトルを生成するための抽象インターフェース。
    具体的な実装はインフラストラクチャ層で行う。
    """

    @abstractmethod
    async def generate_embedding(self, text: str) -> EmbeddingResult:
        """単一のテキストから埋め込みベクトルを生成する。

        Args:
            text: 埋め込みを生成するテキスト

        Returns:
            埋め込みベクトル生成結果

        Raises:
            ValueError: テキストが空または無効な場合
            Exception: 埋め込み生成処理でエラーが発生した場合
        """
        pass

    @abstractmethod
    async def generate_batch_embeddings(
        self, texts: list[str]
    ) -> list[EmbeddingResult]:
        """複数のテキストから埋め込みベクトルをバッチ生成する。

        Args:
            texts: 埋め込みを生成するテキストのリスト

        Returns:
            埋め込みベクトル生成結果のリスト

        Raises:
            ValueError: テキストリストが空または無効な場合
            Exception: 埋め込み生成処理でエラーが発生した場合
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
    def get_dimensions(self) -> int:
        """埋め込みベクトルの次元数を取得する。

        Returns:
            次元数
        """
        pass
