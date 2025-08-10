"""ベンチマークテスト用の共通フィクスチャと設定。"""

import asyncio
import tempfile
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.search_documents import SearchDocumentsUseCase
from src.infrastructure.config.settings import Settings
from src.infrastructure.database.connection import create_all_tables, db_manager
from src.infrastructure.database.models import DocumentChunkModel, DocumentModel
from src.infrastructure.externals.embeddings import MockEmbeddingService
from src.infrastructure.repositories import (
    DocumentRepositoryImpl,
    PgVectorRepositoryImpl,
)
from tests.fixtures.vector_data_generator import (
    TestDataConfig,
    VectorDataGenerator,
    create_performance_test_data,
)


@pytest.fixture(scope="session")
def event_loop() -> Any:
    """セッションスコープのイベントループ。"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def benchmark_settings() -> AsyncGenerator[Settings, None]:
    """ベンチマーク用の設定。"""
    with tempfile.TemporaryDirectory() as temp_dir:
        settings = Settings(
            file_storage_path=Path(temp_dir),
            database_url="sqlite+aiosqlite:///:memory:",  # メモリDBで高速化
            embedding_provider="mock",  # モックプロバイダーで実行
        )
        settings.ensure_file_storage_path()
        yield settings


@pytest_asyncio.fixture(scope="session")
async def benchmark_db() -> AsyncGenerator[None, None]:
    """ベンチマーク用のデータベース初期化。"""
    await create_all_tables()
    yield
    await db_manager.close()


@pytest_asyncio.fixture
async def benchmark_session(
    benchmark_db: None,
) -> AsyncGenerator[AsyncSession, None]:
    """ベンチマーク用のデータベースセッション。"""
    async with db_manager.session() as session:
        yield session


@pytest_asyncio.fixture(scope="session")
async def large_dataset(
    benchmark_db: None,
) -> AsyncGenerator[tuple[list[DocumentModel], list[DocumentChunkModel]], None]:
    """大規模データセットの生成と永続化。

    1000文書、10000チャンクのデータセットを生成してDBに保存。
    """
    documents, chunks = create_performance_test_data(
        num_documents=1000,
        chunks_per_document=10,
    )

    # DBに保存
    async with db_manager.session() as session:
        # DocumentModelに変換
        doc_models = []
        for doc in documents:
            doc_model = DocumentModel(
                id=doc.id.value,
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
            doc_models.append(doc_model)
            session.add(doc_model)

        # DocumentChunkModelに変換
        chunk_models = []
        for chunk in chunks:
            chunk_model = DocumentChunkModel(
                id=chunk.id,
                document_id=chunk.document_id.value,
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
            chunk_models.append(chunk_model)
            session.add(chunk_model)

        await session.commit()

    yield doc_models, chunk_models


@pytest_asyncio.fixture
async def search_use_case(
    benchmark_session: AsyncSession,
) -> SearchDocumentsUseCase:
    """検索ユースケースのインスタンス。"""
    doc_repo = DocumentRepositoryImpl(benchmark_session)
    vector_repo = PgVectorRepositoryImpl(benchmark_session)
    embedding_service = MockEmbeddingService()

    return SearchDocumentsUseCase(
        document_repository=doc_repo,
        vector_search_repository=vector_repo,
        embedding_service=embedding_service,
    )


@pytest.fixture
def benchmark_queries() -> list[tuple[str, list[float]]]:
    """ベンチマーク用の検索クエリ。"""
    generator = VectorDataGenerator(TestDataConfig(seed=42))
    return generator.generate_search_queries(num_queries=100)


@pytest.fixture
def small_dataset() -> tuple[list[Any], list[Any]]:
    """小規模データセット（100文書）。"""
    documents, chunks = create_performance_test_data(
        num_documents=100,
        chunks_per_document=5,
    )
    return documents, chunks


@pytest.fixture
def medium_dataset() -> tuple[list[Any], list[Any]]:
    """中規模データセット（500文書）。"""
    documents, chunks = create_performance_test_data(
        num_documents=500,
        chunks_per_document=8,
    )
    return documents, chunks
