"""ベクトル検索リポジトリのインターフェース。

DDDの原則に従い、ドメイン層にインターフェースを定義。
具体的な実装はインフラストラクチャ層で行う。
"""

from abc import ABC, abstractmethod

from ..value_objects import DocumentId, VectorSearchResult


class VectorSearchRepository(ABC):
    """ベクトル検索リポジトリのインターフェース。

    DDDのリポジトリパターンに従い、永続化の詳細を隠蔽する。
    """

    @abstractmethod
    async def search_similar_chunks(
        self,
        query_embedding: list[float],
        limit: int = 10,
        similarity_threshold: float = 0.7,
        document_ids: list[DocumentId] | None = None,
    ) -> list[VectorSearchResult]:
        """類似チャンクを検索する。

        Args:
            query_embedding: クエリの埋め込みベクトル
            limit: 返す結果の最大数
            similarity_threshold: 類似度の閾値（0.0〜1.0）
            document_ids: 検索対象を特定の文書に限定する場合のID列

        Returns:
            類似度の高い順にソートされた検索結果のリスト
        """
        pass

    @abstractmethod
    async def save_chunk_embedding(
        self,
        chunk_id: str,
        embedding: list[float],
    ) -> None:
        """チャンクの埋め込みベクトルを保存する。

        Args:
            chunk_id: チャンクID
            embedding: 埋め込みベクトル
        """
        pass

    @abstractmethod
    async def save_chunk_embeddings_batch(
        self,
        chunk_embeddings: list[tuple[str, list[float]]],
    ) -> None:
        """複数のチャンク埋め込みをバッチで保存する。

        Args:
            chunk_embeddings: (chunk_id, embedding)のタプルのリスト
        """
        pass

    @abstractmethod
    async def delete_chunk_embeddings(
        self,
        document_id: DocumentId,
    ) -> None:
        """指定された文書のすべてのチャンク埋め込みを削除する。

        Args:
            document_id: 文書ID
        """
        pass

    @abstractmethod
    async def get_chunk_embedding(
        self,
        chunk_id: str,
    ) -> list[float] | None:
        """チャンクの埋め込みベクトルを取得する。

        Args:
            chunk_id: チャンクID

        Returns:
            埋め込みベクトル、存在しない場合はNone
        """
        pass

    @abstractmethod
    async def has_embedding(
        self,
        chunk_id: str,
    ) -> bool:
        """チャンクが埋め込みベクトルを持っているか確認する。

        Args:
            chunk_id: チャンクID

        Returns:
            埋め込みが存在する場合True
        """
        pass
