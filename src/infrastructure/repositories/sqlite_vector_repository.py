"""SQLiteベースのベクトル検索リポジトリの実装。

SQLiteではネイティブなベクトル検索機能がないため、
Pythonでコサイン類似度計算を行う実装。
"""

import json

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...domain.repositories import VectorSearchRepository
from ...domain.value_objects import DocumentId, VectorSearchResult
from ..database.models import DocumentChunkModel, DocumentModel


class SQLiteVectorSearchRepository(VectorSearchRepository):
    """SQLiteを使用したベクトル検索リポジトリの実装。

    pgvectorのようなネイティブ機能がないため、
    全チャンクをメモリに読み込んでPythonで類似度計算を行う。
    """

    def __init__(self, session: AsyncSession):
        """初期化する。

        Args:
            session: 非同期データベースセッション
        """
        self._session = session

    @staticmethod
    def _cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
        """コサイン類似度を計算する。

        Args:
            vec1: ベクトル1
            vec2: ベクトル2

        Returns:
            コサイン類似度（0.0〜1.0）
        """
        try:
            arr1 = np.array(vec1)
            arr2 = np.array(vec2)

            dot_product = np.dot(arr1, arr2)
            norm1 = np.linalg.norm(arr1)
            norm2 = np.linalg.norm(arr2)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            similarity = dot_product / (norm1 * norm2)
            # -1.0 to 1.0 の範囲を 0.0 to 1.0 に正規化
            return float((similarity + 1.0) / 2.0)
        except Exception:
            return 0.0

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
        # クエリを構築
        query = select(DocumentChunkModel, DocumentModel.title).join(
            DocumentModel, DocumentChunkModel.document_id == DocumentModel.id
        )

        # 特定の文書に限定する場合
        if document_ids:
            doc_id_strings = [doc_id.value for doc_id in document_ids]
            query = query.where(DocumentChunkModel.document_id.in_(doc_id_strings))

        # 全チャンクを取得
        result = await self._session.execute(query)

        # 類似度を計算して結果を収集
        search_results = []
        for row in result:
            chunk_model = row[0]
            document_title = row[1]

            # embedingがない場合はスキップ
            embedding_value = getattr(chunk_model, "embedding", None)
            if not embedding_value:
                continue

            # JSON形式のembeddingをパース
            try:
                if isinstance(embedding_value, str):
                    chunk_embedding = json.loads(embedding_value)
                else:
                    chunk_embedding = embedding_value
            except (json.JSONDecodeError, TypeError):
                continue

            # 類似度を計算
            similarity_score = self._cosine_similarity(query_embedding, chunk_embedding)

            # 閾値以上の場合のみ結果に追加
            if similarity_score >= similarity_threshold:
                # チャンクメタデータからインデックスを取得
                chunk_metadata = chunk_model.chunk_metadata or {}
                chunk_index = chunk_metadata.get("chunk_index", 0)

                search_results.append(
                    VectorSearchResult(
                        chunk_id=chunk_model.id,
                        document_id=DocumentId(value=str(chunk_model.document_id)),
                        content=chunk_model.content,
                        similarity_score=similarity_score,
                        chunk_index=chunk_index,
                        document_title=document_title,
                    )
                )

        # 類似度でソートして上位N件を返す
        search_results.sort(key=lambda x: x.similarity_score, reverse=True)
        return search_results[:limit]

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
        # チャンクを取得
        stmt = select(DocumentChunkModel).where(DocumentChunkModel.id == chunk_id)
        result = await self._session.execute(stmt)
        chunk = result.scalar_one_or_none()

        if chunk:
            # JSON形式で保存
            chunk.embedding = json.dumps(embedding)  # type: ignore[assignment]
            await self._session.commit()

    async def save_chunk_embeddings_batch(
        self,
        chunk_embeddings: list[tuple[str, list[float]]],
    ) -> None:
        """複数のチャンク埋め込みをバッチで保存する。

        Args:
            chunk_embeddings: (chunk_id, embedding)のタプルのリスト
        """
        for chunk_id, embedding in chunk_embeddings:
            await self.save_chunk_embedding(chunk_id, embedding)

    async def delete_chunk_embeddings(
        self,
        document_id: DocumentId,
    ) -> None:
        """指定された文書のすべてのチャンク埋め込みを削除する。

        Args:
            document_id: 文書ID
        """
        # チャンクを取得
        stmt = select(DocumentChunkModel).where(
            DocumentChunkModel.document_id == document_id.value
        )
        result = await self._session.execute(stmt)
        chunks = result.scalars().all()

        # embeddingをNULLに設定
        for chunk in chunks:
            chunk.embedding = None  # type: ignore[assignment]

        await self._session.commit()

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
        stmt = select(DocumentChunkModel).where(DocumentChunkModel.id == chunk_id)
        result = await self._session.execute(stmt)
        chunk = result.scalar_one_or_none()

        if chunk:
            embedding_value = getattr(chunk, "embedding", None)
            if embedding_value:
                try:
                    if isinstance(embedding_value, str):
                        return json.loads(embedding_value)  # type: ignore[no-any-return]
                    else:
                        return embedding_value  # type: ignore[no-any-return]
                except (json.JSONDecodeError, TypeError):
                    return None

        return None

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
        embedding = await self.get_chunk_embedding(chunk_id)
        return embedding is not None
