"""モックベクトル検索リポジトリの実装。

開発環境でベクトル検索機能をテストするための実装。
"""

import random

from ...domain.repositories import VectorSearchRepository
from ...domain.value_objects import (
    ChunkMetadata,
    DocumentChunk,
    DocumentId,
    VectorSearchResult,
)


class MockVectorSearchRepository(VectorSearchRepository):
    """モックベクトル検索リポジトリ。

    実際のベクトル検索は行わず、ダミーの結果を返す。
    """

    def __init__(self) -> None:
        """初期化。"""
        self.chunks: list[DocumentChunk] = []
        self.embeddings: dict[str, list[float]] = {}

    async def search_similar_chunks(
        self,
        query_embedding: list[float],
        limit: int = 10,
        similarity_threshold: float = 0.7,
        document_ids: list[DocumentId] | None = None,
    ) -> list[VectorSearchResult]:
        """類似チャンクを検索する（モック）。

        Args:
            query_embedding: クエリの埋め込みベクトル
            limit: 返す結果の最大数
            similarity_threshold: 類似度の閾値
            document_ids: 検索対象を特定の文書に限定する場合のID列

        Returns:
            検索結果リスト
        """
        # モックデータを生成
        mock_results = []

        # テスト用のモックチャンクを生成
        doc_id = DocumentId.generate()
        mock_chunks = [
            DocumentChunk(
                id="mock-chunk-1",
                document_id=doc_id,
                content="RAGシステム（Retrieval-Augmented Generation）は、大規模言語モデル（LLM）と情報検索システムを組み合わせた技術です。",
                embedding=None,
                metadata=ChunkMetadata(
                    chunk_index=0, start_position=0, end_position=80, total_chunks=3
                ),
            ),
            DocumentChunk(
                id="mock-chunk-2",
                document_id=doc_id,
                content="ユーザーの質問に対して、まず関連する文書を検索し、その情報を基にLLMが回答を生成します。",
                embedding=None,
                metadata=ChunkMetadata(
                    chunk_index=1, start_position=80, end_position=150, total_chunks=3
                ),
            ),
            DocumentChunk(
                id="mock-chunk-3",
                document_id=doc_id,
                content="これにより、最新の情報や専門的な知識に基づいた正確な回答が可能になります。",
                embedding=None,
                metadata=ChunkMetadata(
                    chunk_index=2, start_position=150, end_position=210, total_chunks=3
                ),
            ),
        ]

        # 上位k件を返す
        for i, chunk in enumerate(mock_chunks[: min(limit, len(mock_chunks))]):
            # ランダムな類似度スコアを生成（0.7-0.95の範囲）
            score = 0.95 - (i * 0.1) + random.uniform(-0.05, 0.05)
            score = max(0.0, min(1.0, score))

            if score >= similarity_threshold:
                mock_results.append(
                    VectorSearchResult(
                        chunk_id=chunk.id,
                        document_id=chunk.document_id,
                        content=chunk.content,
                        similarity_score=score,
                        chunk_index=chunk.metadata.chunk_index,
                        document_title="RAGシステムの概要",
                    )
                )

        return mock_results

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
        self.embeddings[chunk_id] = embedding

    async def save_chunk_embeddings_batch(
        self,
        chunk_embeddings: list[tuple[str, list[float]]],
    ) -> None:
        """複数のチャンク埋め込みをバッチで保存する。

        Args:
            chunk_embeddings: (chunk_id, embedding)のタプルのリスト
        """
        for chunk_id, embedding in chunk_embeddings:
            self.embeddings[chunk_id] = embedding

    async def delete_chunk_embeddings(
        self,
        document_id: DocumentId,
    ) -> None:
        """指定された文書のすべてのチャンク埋め込みを削除する。

        Args:
            document_id: 文書ID
        """
        # メモリから削除
        self.chunks = [c for c in self.chunks if c.document_id != str(document_id)]
        # 埋め込みも削除（実際のチャンクIDとの関連付けが必要な場合）
        # ここではモック実装なので簡略化

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
        return self.embeddings.get(chunk_id)

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
        return chunk_id in self.embeddings
