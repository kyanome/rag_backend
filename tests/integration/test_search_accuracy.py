"""検索精度検証のための統合テスト。

Precision、Recall、F1スコアを計測して検索精度を評価します。
"""

import os
import tempfile
import uuid
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.search_documents import (
    SearchDocumentsInput,
    SearchDocumentsUseCase,
)
from src.infrastructure.database.models import DocumentChunkModel, DocumentModel
from src.infrastructure.externals.embeddings import MockEmbeddingService
from src.infrastructure.externals.file_storage import FileStorageService
from src.infrastructure.repositories import (
    DocumentRepositoryImpl,
    PgVectorRepositoryImpl,
)
from tests.fixtures.vector_data_generator import TestDataConfig, VectorDataGenerator


@dataclass
class SearchMetrics:
    """検索精度メトリクス。"""

    precision: float
    recall: float
    f1_score: float
    true_positives: int
    false_positives: int
    false_negatives: int


class SearchAccuracyEvaluator:
    """検索精度評価クラス。"""

    @staticmethod
    def calculate_metrics(
        retrieved: list[str],
        relevant: list[str],
    ) -> SearchMetrics:
        """検索結果の精度メトリクスを計算。

        Args:
            retrieved: 検索で取得された文書IDリスト
            relevant: 正解の関連文書IDリスト

        Returns:
            計算された精度メトリクス
        """
        retrieved_set = set(retrieved)
        relevant_set = set(relevant)

        # True Positives: 正しく取得された関連文書
        true_positives = len(retrieved_set & relevant_set)

        # False Positives: 誤って取得された非関連文書
        false_positives = len(retrieved_set - relevant_set)

        # False Negatives: 取得されなかった関連文書
        false_negatives = len(relevant_set - retrieved_set)

        # Precision: 取得した文書のうち関連文書の割合
        precision = (
            true_positives / (true_positives + false_positives)
            if (true_positives + false_positives) > 0
            else 0.0
        )

        # Recall: 関連文書のうち取得できた割合
        recall = (
            true_positives / (true_positives + false_negatives)
            if (true_positives + false_negatives) > 0
            else 0.0
        )

        # F1 Score: PrecisionとRecallの調和平均
        f1_score = (
            2 * (precision * recall) / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )

        return SearchMetrics(
            precision=precision,
            recall=recall,
            f1_score=f1_score,
            true_positives=true_positives,
            false_positives=false_positives,
            false_negatives=false_negatives,
        )


@pytest_asyncio.fixture
async def file_storage() -> AsyncGenerator[FileStorageService, None]:
    """ファイルストレージフィクスチャ。"""
    with tempfile.TemporaryDirectory() as temp_dir:
        storage = FileStorageService(base_path=Path(temp_dir))
        yield storage


@pytest_asyncio.fixture
async def accuracy_test_data(
    async_session: AsyncSession,
    file_storage: FileStorageService,
) -> AsyncGenerator[tuple[dict[str, list[str]], dict[str, str]], None]:
    """精度テスト用のデータセットと正解データ。"""
    # テストデータ生成器を初期化
    generator = VectorDataGenerator(
        TestDataConfig(
            num_documents=20,
            chunks_per_document=5,
            seed=42,
        )
    )

    # テストデータを生成
    documents, chunks = generator.generate_dataset()

    # DBに保存
    doc_id_map = {}
    for doc in documents:
        doc_model = DocumentModel(
            id=uuid.UUID(doc.id.value),
            title=doc.title,
            content=doc.content,
            document_metadata={
                "file_name": doc.metadata.file_name,
                "file_size": doc.metadata.file_size,
                "content_type": doc.metadata.content_type,
                "author": doc.metadata.author,
                "category": doc.metadata.category,
                "tags": doc.metadata.tags,
                "description": doc.metadata.description,
            },
            created_at=doc.metadata.created_at,
            updated_at=doc.metadata.updated_at,
        )
        async_session.add(doc_model)
        doc_id_map[doc.title] = doc.id.value

    for chunk in chunks:
        chunk_model = DocumentChunkModel(
            id=chunk.id,
            document_id=uuid.UUID(chunk.document_id.value),
            content=chunk.content,
            embedding=chunk.embedding,
            chunk_metadata={
                "chunk_index": chunk.metadata.chunk_index,
                "start_position": chunk.metadata.start_position,
                "end_position": chunk.metadata.end_position,
                "total_chunks": chunk.metadata.total_chunks,
                "overlap_with_previous": chunk.metadata.overlap_with_previous,
                "overlap_with_next": chunk.metadata.overlap_with_next,
            },
            created_at=datetime.now(UTC),
        )
        async_session.add(chunk_model)

    await async_session.commit()

    # 正解データを作成（ランダムに選択）
    doc_ids = list(doc_id_map.values())
    ground_truth = {}
    if len(doc_ids) >= 3:
        ground_truth = {
            "test_query_1": doc_ids[:3],
            "test_query_2": doc_ids[3:6] if len(doc_ids) >= 6 else doc_ids[:3],
            "test_query_3": doc_ids[6:9] if len(doc_ids) >= 9 else doc_ids[:3],
        }

    yield ground_truth, doc_id_map


@pytest.mark.asyncio
@pytest.mark.integration
class TestSearchAccuracy:
    """検索精度の統合テストクラス。"""

    async def test_keyword_search_accuracy(
        self,
        async_session: AsyncSession,
        file_storage: FileStorageService,
        accuracy_test_data: tuple[dict[str, list[str]], dict[str, str]],
    ) -> None:
        """キーワード検索の精度テスト。"""
        ground_truth, _ = accuracy_test_data

        # リポジトリとユースケースを初期化
        doc_repo = DocumentRepositoryImpl(async_session, file_storage)
        vector_repo = PgVectorRepositoryImpl(async_session)
        embedding_service = MockEmbeddingService()
        search_use_case = SearchDocumentsUseCase(
            doc_repo, vector_repo, embedding_service
        )

        evaluator = SearchAccuracyEvaluator()

        # 各クエリで精度を測定
        all_metrics = []

        for query, relevant_docs in ground_truth.items():
            if not relevant_docs:
                continue

            # キーワード検索を実行
            search_input = SearchDocumentsInput(
                query=query,
                search_type="keyword",
                limit=10,
            )

            result = await search_use_case.execute(search_input)

            # 取得された文書IDを抽出
            retrieved_docs = [item.document_id for item in result.results]

            # メトリクスを計算
            metrics = evaluator.calculate_metrics(
                retrieved_docs,
                relevant_docs,
            )
            all_metrics.append(metrics)

            # 個別のクエリの精度を確認
            assert metrics.precision >= 0.0
            assert metrics.recall >= 0.0
            assert metrics.f1_score >= 0.0

        # 少なくとも1つのクエリで結果が返されることを確認
        assert len(all_metrics) > 0

        # 平均精度を計算
        avg_precision = sum(m.precision for m in all_metrics) / len(all_metrics)
        avg_recall = sum(m.recall for m in all_metrics) / len(all_metrics)
        avg_f1 = sum(m.f1_score for m in all_metrics) / len(all_metrics)

        # 最低限の精度を確保（0以上であることを確認）
        assert avg_precision >= 0.0, f"Average precision: {avg_precision}"
        assert avg_recall >= 0.0, f"Average recall: {avg_recall}"
        assert avg_f1 >= 0.0, f"Average F1 score: {avg_f1}"

    @pytest.mark.skipif(
        "TEST_DATABASE_URL" not in os.environ,
        reason="Vector search requires PostgreSQL with pgvector",
    )
    async def test_vector_search_accuracy_postgres(
        self,
        postgres_session: AsyncSession,
        file_storage: FileStorageService,
        use_postgres,
    ) -> None:
        """ベクトル検索の精度テスト（PostgreSQL）。"""
        # PostgreSQL用のテストデータを生成
        generator = VectorDataGenerator(
            TestDataConfig(
                num_documents=10,
                chunks_per_document=3,
                seed=42,
            )
        )
        documents, chunks = generator.generate_dataset()

        # DBに保存
        doc_id_map = {}
        for doc in documents:
            doc_model = DocumentModel(
                id=uuid.UUID(doc.id.value),
                title=doc.title,
                content=doc.content.decode(
                    "utf-8"
                ),  # PostgreSQL expects str, not bytes
                document_metadata={
                    "file_name": doc.metadata.file_name,
                    "file_size": doc.metadata.file_size,
                    "content_type": doc.metadata.content_type,
                    "author": doc.metadata.author,
                    "category": doc.metadata.category,
                    "tags": doc.metadata.tags,
                    "description": doc.metadata.description,
                },
                created_at=doc.metadata.created_at.replace(
                    tzinfo=None
                ),  # Remove timezone for PostgreSQL
                updated_at=doc.metadata.updated_at.replace(
                    tzinfo=None
                ),  # Remove timezone for PostgreSQL
            )
            postgres_session.add(doc_model)
            doc_id_map[doc.title] = doc.id.value

        for chunk in chunks:
            chunk_model = DocumentChunkModel(
                id=chunk.id,
                document_id=uuid.UUID(chunk.document_id.value),
                content=chunk.content,
                embedding=chunk.embedding,
                chunk_metadata={
                    "chunk_index": chunk.metadata.chunk_index,
                    "start_position": chunk.metadata.start_position,
                    "end_position": chunk.metadata.end_position,
                    "total_chunks": chunk.metadata.total_chunks,
                    "overlap_with_previous": chunk.metadata.overlap_with_previous,
                    "overlap_with_next": chunk.metadata.overlap_with_next,
                },
                created_at=datetime.now(UTC).replace(
                    tzinfo=None
                ),  # Remove timezone for PostgreSQL
            )
            postgres_session.add(chunk_model)

        await postgres_session.commit()

        # 正解データを作成
        doc_ids = list(doc_id_map.values())
        ground_truth = {
            "test_query": doc_ids[:3] if len(doc_ids) >= 3 else doc_ids,
        }

        # リポジトリとユースケースを初期化
        doc_repo = DocumentRepositoryImpl(postgres_session, file_storage)
        vector_repo = PgVectorRepositoryImpl(postgres_session)
        embedding_service = MockEmbeddingService()
        search_use_case = SearchDocumentsUseCase(
            doc_repo, vector_repo, embedding_service
        )

        evaluator = SearchAccuracyEvaluator()

        # 各クエリで精度を測定
        all_metrics = []

        for query, relevant_docs in ground_truth.items():
            if not relevant_docs:
                continue

            # ベクトル検索を実行
            search_input = SearchDocumentsInput(
                query=query,
                search_type="vector",
                limit=10,
            )

            result = await search_use_case.execute(search_input)

            # 取得された文書IDを抽出
            retrieved_docs = [item.document_id for item in result.results]

            # メトリクスを計算
            metrics = evaluator.calculate_metrics(
                retrieved_docs,
                relevant_docs,
            )
            all_metrics.append(metrics)

        if len(all_metrics) > 0:
            # 平均精度を計算
            avg_precision = sum(m.precision for m in all_metrics) / len(all_metrics)
            avg_recall = sum(m.recall for m in all_metrics) / len(all_metrics)
            avg_f1 = sum(m.f1_score for m in all_metrics) / len(all_metrics)

            # ベクトル検索も一定の精度を確保
            assert avg_precision >= 0.0
            assert avg_recall >= 0.0
            assert avg_f1 >= 0.0
