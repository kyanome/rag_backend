"""PgVectorRepositoryImplの統合テスト。"""

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.value_objects import DocumentId, VectorSearchResult
from src.infrastructure.database.models import DocumentChunkModel, DocumentModel
from src.infrastructure.repositories import PgVectorRepositoryImpl


@pytest.mark.asyncio
class TestPgVectorRepository:
    """PgVectorRepositoryImplの統合テストクラス。"""

    async def setup_test_data(self, session: AsyncSession) -> tuple[str, str, str]:
        """テスト用データをセットアップする。

        Returns:
            (document_id, chunk_id_1, chunk_id_2)のタプル
        """
        # テスト用文書を作成
        doc_id = str(uuid.uuid4())
        doc_model = DocumentModel(
            id=uuid.UUID(doc_id),
            title="Test Document",
            content="",
            document_metadata={
                "file_name": "test.txt",
                "file_size": 100,
                "content_type": "text/plain",
                "tags": [],
            },
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        session.add(doc_model)

        # テスト用チャンクを作成（埋め込みベクトル付き）
        chunk_id_1 = str(uuid.uuid4())
        chunk_1 = DocumentChunkModel(
            id=chunk_id_1,
            document_id=uuid.UUID(doc_id),
            content="This is the first test chunk",
            embedding=[0.1] * 1536,  # ダミーの埋め込みベクトル
            chunk_metadata={
                "chunk_index": 0,
                "start_position": 0,
                "end_position": 30,
                "total_chunks": 2,
            },
        )
        session.add(chunk_1)

        chunk_id_2 = str(uuid.uuid4())
        chunk_2 = DocumentChunkModel(
            id=chunk_id_2,
            document_id=uuid.UUID(doc_id),
            content="This is the second test chunk",
            embedding=[0.2] * 1536,  # 異なる埋め込みベクトル
            chunk_metadata={
                "chunk_index": 1,
                "start_position": 30,
                "end_position": 60,
                "total_chunks": 2,
            },
        )
        session.add(chunk_2)

        await session.commit()
        return doc_id, chunk_id_1, chunk_id_2

    async def test_save_and_get_chunk_embedding(self, async_session: AsyncSession):
        """チャンクの埋め込みベクトルの保存と取得をテスト。"""
        repo = PgVectorRepositoryImpl(async_session)
        doc_id, chunk_id, _ = await self.setup_test_data(async_session)

        # 新しい埋め込みベクトルを保存
        test_embedding = [0.5] * 1536
        await repo.save_chunk_embedding(chunk_id, test_embedding)
        await async_session.commit()

        # 保存した埋め込みを取得
        retrieved_embedding = await repo.get_chunk_embedding(chunk_id)

        assert retrieved_embedding is not None
        assert len(retrieved_embedding) == 1536
        assert retrieved_embedding[0] == pytest.approx(0.5)

    async def test_has_embedding(self, async_session: AsyncSession):
        """埋め込みの存在確認をテスト。"""
        repo = PgVectorRepositoryImpl(async_session)
        doc_id, chunk_id, _ = await self.setup_test_data(async_session)

        # 埋め込みが存在することを確認
        has_embedding = await repo.has_embedding(chunk_id)
        assert has_embedding is True

        # 存在しないチャンクID
        non_existent = await repo.has_embedding("non-existent-id")
        assert non_existent is False

    async def test_save_chunk_embeddings_batch(self, async_session: AsyncSession):
        """バッチでの埋め込み保存をテスト。"""
        repo = PgVectorRepositoryImpl(async_session)
        doc_id, chunk_id_1, chunk_id_2 = await self.setup_test_data(async_session)

        # バッチで埋め込みを更新
        batch_embeddings = [
            (chunk_id_1, [0.7] * 1536),
            (chunk_id_2, [0.8] * 1536),
        ]
        await repo.save_chunk_embeddings_batch(batch_embeddings)
        await async_session.commit()

        # 更新された埋め込みを確認
        embedding_1 = await repo.get_chunk_embedding(chunk_id_1)
        embedding_2 = await repo.get_chunk_embedding(chunk_id_2)

        assert embedding_1 is not None
        assert embedding_1[0] == pytest.approx(0.7)
        assert embedding_2 is not None
        assert embedding_2[0] == pytest.approx(0.8)

    async def test_delete_chunk_embeddings(self, async_session: AsyncSession):
        """文書のチャンク埋め込みの削除をテスト。"""
        repo = PgVectorRepositoryImpl(async_session)
        doc_id, chunk_id_1, chunk_id_2 = await self.setup_test_data(async_session)

        # 文書のすべてのチャンク埋め込みを削除
        await repo.delete_chunk_embeddings(DocumentId(value=doc_id))
        await async_session.commit()

        # 埋め込みが削除されたことを確認
        has_embedding_1 = await repo.has_embedding(chunk_id_1)
        has_embedding_2 = await repo.has_embedding(chunk_id_2)

        assert has_embedding_1 is False
        assert has_embedding_2 is False

    async def test_search_similar_chunks(self, async_session: AsyncSession):
        """類似チャンク検索をテスト（pgvectorが利用可能な場合のみ）。"""
        # SQLiteでは<=>演算子が使えないためスキップ
        if async_session.bind.dialect.name == "sqlite":
            pytest.skip("pgvector search not supported in SQLite")

        repo = PgVectorRepositoryImpl(async_session)

        # pgvectorを使用する場合のみテスト
        # このテストはPostgreSQLとpgvectorが実際に動作している環境でのみ実行される
        try:
            import importlib.util

            spec = importlib.util.find_spec("pgvector.sqlalchemy")
            if spec is None:
                pytest.skip("pgvector not available for testing")

            doc_id, chunk_id_1, chunk_id_2 = await self.setup_test_data(async_session)

            # クエリベクトル（chunk_1に近い）
            query_embedding = [0.11] * 1536

            # 類似検索を実行
            results = await repo.search_similar_chunks(
                query_embedding=query_embedding,
                limit=5,
                similarity_threshold=0.0,  # すべての結果を取得
            )

            # 結果の検証
            assert len(results) > 0
            assert isinstance(results[0], VectorSearchResult)
            assert results[0].similarity_score >= 0.0
            assert results[0].similarity_score <= 1.0

            # 類似度順にソートされていることを確認
            if len(results) > 1:
                for i in range(len(results) - 1):
                    assert (
                        results[i].similarity_score >= results[i + 1].similarity_score
                    )

        except ImportError:
            pytest.skip("pgvector not available for testing")
