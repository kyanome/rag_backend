"""pgvectorを使用したベクトル検索リポジトリの実装。"""

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ...domain.repositories import VectorSearchRepository
from ...domain.value_objects import DocumentId, VectorSearchResult
from ..database.models import DocumentChunkModel, DocumentModel


class PgVectorRepositoryImpl(VectorSearchRepository):
    """PostgreSQL pgvectorを使用したベクトル検索リポジトリの実装。"""

    def __init__(self, session: AsyncSession):
        """初期化する。

        Args:
            session: 非同期データベースセッション
        """
        self._session = session

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
        # PostgreSQLのpgvectorを使用したコサイン類似度検索
        # 1 - (embedding <=> query) でコサイン類似度を計算
        query = (
            select(
                DocumentChunkModel,
                DocumentModel.title,
                text("1 - (embedding_vector <=> :query_vector) AS similarity"),
            )
            .join(DocumentModel, DocumentChunkModel.document_id == DocumentModel.id)
            .where(text("1 - (embedding_vector <=> :query_vector) >= :threshold"))
        )

        # 特定の文書に限定する場合
        if document_ids:
            doc_id_strings = [doc_id.value for doc_id in document_ids]
            query = query.where(DocumentChunkModel.document_id.in_(doc_id_strings))

        # 類似度でソートして制限
        query = query.order_by(text("similarity DESC")).limit(limit)

        # パラメータをバインドして実行
        # pgvectorは[1,2,3]形式の文字列として受け取る
        query_vector_str = "[" + ",".join(map(str, query_embedding)) + "]"
        result = await self._session.execute(
            query,
            {
                "query_vector": query_vector_str,
                "threshold": similarity_threshold,
            },
        )

        # 結果を値オブジェクトに変換
        search_results = []
        for row in result:
            chunk_model = row[0]
            document_title = row[1]
            similarity_score = row[2]

            # チャンクメタデータからインデックスを取得
            chunk_metadata = chunk_model.chunk_metadata or {}
            chunk_index = chunk_metadata.get("chunk_index", 0)

            search_results.append(
                VectorSearchResult(
                    chunk_id=chunk_model.id,
                    document_id=DocumentId(value=str(chunk_model.document_id)),
                    content=chunk_model.content,
                    similarity_score=float(similarity_score),
                    chunk_index=chunk_index,
                    document_title=document_title,
                )
            )

        return search_results

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
        query = select(DocumentChunkModel).where(DocumentChunkModel.id == chunk_id)
        result = await self._session.execute(query)
        chunk_model = result.scalar_one_or_none()

        if chunk_model:
            # 埋め込みベクトルを更新
            chunk_model.embedding_vector = embedding  # type: ignore[assignment]
            chunk_model.embedding = embedding  # type: ignore[assignment]
            await self._session.flush()

    async def save_chunk_embeddings_batch(
        self,
        chunk_embeddings: list[tuple[str, list[float]]],
    ) -> None:
        """複数のチャンク埋め込みをバッチで保存する。

        Args:
            chunk_embeddings: (chunk_id, embedding)のタプルのリスト
        """
        # バッチ更新のためのクエリを構築
        for chunk_id, embedding in chunk_embeddings:
            query = select(DocumentChunkModel).where(DocumentChunkModel.id == chunk_id)
            result = await self._session.execute(query)
            chunk_model = result.scalar_one_or_none()

            if chunk_model:
                chunk_model.embedding_vector = embedding  # type: ignore[assignment]
                chunk_model.embedding = embedding  # type: ignore[assignment]

        await self._session.flush()

    async def delete_chunk_embeddings(
        self,
        document_id: DocumentId,
    ) -> None:
        """指定された文書のすべてのチャンク埋め込みを削除する。

        Args:
            document_id: 文書ID
        """
        # 文書IDでチャンクを取得
        query = select(DocumentChunkModel).where(
            DocumentChunkModel.document_id == document_id.value
        )
        result = await self._session.execute(query)
        chunks = result.scalars().all()

        # 埋め込みをnullに設定
        for chunk in chunks:
            chunk.embedding_vector = None  # type: ignore[assignment]
            chunk.embedding = None  # type: ignore[assignment]

        await self._session.flush()

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
        query = select(DocumentChunkModel).where(DocumentChunkModel.id == chunk_id)
        result = await self._session.execute(query)
        chunk_model = result.scalar_one_or_none()

        if chunk_model:
            # pgvectorからの取得を優先、なければJSONから
            if (
                hasattr(chunk_model, "embedding_vector")
                and chunk_model.embedding_vector is not None
            ):
                return list(chunk_model.embedding_vector)
            elif chunk_model.embedding is not None:
                return chunk_model.embedding  # type: ignore[return-value]

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
        query = select(DocumentChunkModel).where(DocumentChunkModel.id == chunk_id)
        result = await self._session.execute(query)
        chunk_model = result.scalar_one_or_none()

        if chunk_model:
            # pgvectorまたはJSONのいずれかに埋め込みがあれば
            has_vector = (
                hasattr(chunk_model, "embedding_vector")
                and chunk_model.embedding_vector is not None
            )
            has_json = chunk_model.embedding is not None
            return has_vector or has_json

        return False
