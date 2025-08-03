"""DocumentRepositoryの統合テスト。"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.domain.entities import Document
from src.domain.exceptions import DocumentNotFoundError
from src.domain.value_objects import DocumentChunk, DocumentId, DocumentMetadata
from src.infrastructure.database.connection import Base
from src.infrastructure.externals.file_storage import FileStorageService
from src.infrastructure.repositories.document_repository_impl import (
    DocumentRepositoryImpl,
)


@pytest.fixture
async def db_engine():
    """テスト用のデータベースエンジンを作成する。"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    """テスト用のデータベースセッションを作成する。"""
    async_session = sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session


@pytest.fixture
async def file_storage(tmp_path):
    """テスト用のファイルストレージサービスを作成する。"""
    return FileStorageService(base_path=tmp_path)


@pytest.fixture
async def repository(db_session, file_storage):
    """テスト用のリポジトリインスタンスを作成する。"""
    return DocumentRepositoryImpl(session=db_session, file_storage=file_storage)


@pytest.fixture
def sample_document():
    """テスト用の文書を作成する。"""
    metadata = DocumentMetadata.create_new(
        file_name="integration_test.pdf",
        file_size=2048,
        content_type="application/pdf",
        category="統合テスト",
        tags=["テスト", "統合"],
        author="統合テスト太郎",
        description="統合テスト用の文書",
    )
    return Document.create(
        title="統合テスト文書",
        content=b"Integration test content",
        metadata=metadata,
    )


class TestDocumentRepositoryIntegration:
    """DocumentRepositoryの統合テストクラス。"""

    async def test_save_and_find_by_id(
        self, repository: DocumentRepositoryImpl, sample_document: Document
    ) -> None:
        """文書の保存と検索をテストする。"""
        await repository.save(sample_document)

        found = await repository.find_by_id(sample_document.id)

        assert found is not None
        assert found.id.value == sample_document.id.value
        assert found.title == sample_document.title
        assert found.content == sample_document.content
        assert found.metadata.file_name == sample_document.metadata.file_name
        assert found.metadata.category == sample_document.metadata.category
        assert found.metadata.tags == sample_document.metadata.tags

    async def test_save_with_chunks(
        self, repository: DocumentRepositoryImpl, sample_document: Document
    ) -> None:
        """チャンク付き文書の保存をテストする。"""
        sample_document.add_chunk(
            DocumentChunk.create(
                document_id=sample_document.id,
                content="チャンク1の内容",
                chunk_index=0,
                start_position=0,
                end_position=100,
                total_chunks=2,
            )
        )
        sample_document.add_chunk(
            DocumentChunk.create(
                document_id=sample_document.id,
                content="チャンク2の内容",
                chunk_index=1,
                start_position=80,
                end_position=180,
                total_chunks=2,
                overlap_with_previous=20,
            )
        )

        await repository.save(sample_document)

        found = await repository.find_by_id(sample_document.id)
        assert found is not None
        assert len(found.chunks) == 2
        assert found.chunks[0].content == "チャンク1の内容"
        assert found.chunks[1].content == "チャンク2の内容"

    async def test_update(
        self, repository: DocumentRepositoryImpl, sample_document: Document
    ) -> None:
        """文書の更新をテストする。"""
        await repository.save(sample_document)

        sample_document.title = "更新された文書タイトル"
        sample_document.metadata = sample_document.metadata.model_copy(
            update={"category": "更新カテゴリ"}
        )

        await repository.update(sample_document)

        found = await repository.find_by_id(sample_document.id)
        assert found is not None
        assert found.title == "更新された文書タイトル"
        assert found.metadata.category == "更新カテゴリ"
        assert found.version == 2

    async def test_delete(
        self, repository: DocumentRepositoryImpl, sample_document: Document
    ) -> None:
        """文書の削除をテストする。"""
        await repository.save(sample_document)

        await repository.delete(sample_document.id)

        found = await repository.find_by_id(sample_document.id)
        assert found is None

    async def test_delete_nonexistent(self, repository: DocumentRepositoryImpl) -> None:
        """存在しない文書の削除をテストする。"""
        non_existent_id = DocumentId.generate()

        with pytest.raises(DocumentNotFoundError):
            await repository.delete(non_existent_id)

    async def test_exists(
        self, repository: DocumentRepositoryImpl, sample_document: Document
    ) -> None:
        """文書の存在確認をテストする。"""
        assert not await repository.exists(sample_document.id)

        await repository.save(sample_document)

        assert await repository.exists(sample_document.id)

    async def test_find_all(self, repository: DocumentRepositoryImpl) -> None:
        """全文書の取得をテストする。"""
        documents = []
        for i in range(5):
            doc = Document.create(
                title=f"テスト文書{i}",
                content=f"Content {i}".encode(),
                metadata=DocumentMetadata.create_new(
                    file_name=f"test{i}.txt",
                    file_size=100 + i,
                    content_type="text/plain",
                ),
            )
            documents.append(doc)
            await repository.save(doc)

        result, total = await repository.find_all(skip=0, limit=3)
        assert len(result) == 3
        assert total == 5

        result, total = await repository.find_all(skip=3, limit=3)
        assert len(result) == 2
        assert total == 5

    async def test_find_by_title(self, repository: DocumentRepositoryImpl) -> None:
        """タイトルによる検索をテストする。"""
        doc1 = Document.create(
            title="重要な報告書",
            content=b"Content 1",
            metadata=DocumentMetadata.create_new(
                file_name="report1.pdf",
                file_size=1000,
                content_type="application/pdf",
            ),
        )
        doc2 = Document.create(
            title="月次報告書",
            content=b"Content 2",
            metadata=DocumentMetadata.create_new(
                file_name="report2.pdf",
                file_size=2000,
                content_type="application/pdf",
            ),
        )
        doc3 = Document.create(
            title="プロジェクト計画",
            content=b"Content 3",
            metadata=DocumentMetadata.create_new(
                file_name="plan.pdf",
                file_size=3000,
                content_type="application/pdf",
            ),
        )

        await repository.save(doc1)
        await repository.save(doc2)
        await repository.save(doc3)

        results = await repository.find_by_title("報告書")
        assert len(results) == 2
        titles = [doc.title for doc in results]
        assert "重要な報告書" in titles
        assert "月次報告書" in titles

    async def test_transaction_rollback(
        self, repository: DocumentRepositoryImpl, sample_document: Document
    ) -> None:
        """トランザクションのロールバックをテストする。"""
        sample_document.chunks = [
            DocumentChunk.create(
                document_id=sample_document.id,
                content="チャンク",
                chunk_index=0,
                start_position=0,
                end_position=100,
                total_chunks=1,
            )
        ]

        # ファイルストレージの保存メソッドをモックしてエラーを発生させる
        original_save = repository.file_storage.save

        async def failing_save(*args, **kwargs):
            raise Exception("Simulated error")

        repository.file_storage.save = failing_save

        with pytest.raises(Exception, match="Failed to save document"):
            await repository.save(sample_document)

        # 元に戻す
        repository.file_storage.save = original_save

        found = await repository.find_by_id(sample_document.id)
        assert found is None
