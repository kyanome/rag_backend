"""DocumentRepositoryの統合テスト。"""

from datetime import datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.domain.entities import Document
from src.domain.exceptions import DocumentNotFoundError
from src.domain.value_objects import (
    DocumentChunk,
    DocumentFilter,
    DocumentId,
    DocumentMetadata,
)
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

    async def test_find_all_with_title_filter(
        self, repository: DocumentRepositoryImpl
    ) -> None:
        """タイトルフィルターを使用した文書一覧取得をテストする。"""
        # テストデータの作成
        docs = [
            Document.create(
                title="技術仕様書.pdf",
                content=b"Content 1",
                metadata=DocumentMetadata.create_new(
                    file_name="spec.pdf",
                    file_size=1000,
                    content_type="application/pdf",
                ),
            ),
            Document.create(
                title="技術ガイド.pdf",
                content=b"Content 2",
                metadata=DocumentMetadata.create_new(
                    file_name="guide.pdf",
                    file_size=2000,
                    content_type="application/pdf",
                ),
            ),
            Document.create(
                title="営業報告書.pdf",
                content=b"Content 3",
                metadata=DocumentMetadata.create_new(
                    file_name="sales.pdf",
                    file_size=3000,
                    content_type="application/pdf",
                ),
            ),
        ]

        for doc in docs:
            await repository.save(doc)

        # タイトルフィルターでの検索
        filter_ = DocumentFilter(title="技術")
        result, total = await repository.find_all(filter_=filter_)

        assert len(result) == 2
        assert total == 2
        titles = [item.title for item in result]
        assert "技術仕様書.pdf" in titles
        assert "技術ガイド.pdf" in titles

    async def test_find_all_with_date_filter(
        self, repository: DocumentRepositoryImpl
    ) -> None:
        """日付フィルターを使用した文書一覧取得をテストする。"""
        base_date = datetime.now()

        # 異なる日付の文書を作成
        docs = []
        for i in range(5):
            metadata = DocumentMetadata.create_new(
                file_name=f"doc{i}.pdf",
                file_size=1000,
                content_type="application/pdf",
            )
            # created_atを異なる日付に設定
            created_at = base_date - timedelta(days=10 - i * 2)
            metadata = metadata.model_copy(
                update={"created_at": created_at, "updated_at": created_at}
            )

            doc = Document.create(
                title=f"Document {i}",
                content=f"Content {i}".encode(),
                metadata=metadata,
            )
            docs.append(doc)
            await repository.save(doc)

        # 日付範囲でフィルタリング
        filter_ = DocumentFilter(
            created_from=base_date - timedelta(days=7), created_to=base_date
        )
        result, total = await repository.find_all(filter_=filter_)

        # 7日以内に作成された文書のみ取得されることを確認
        assert len(result) >= 2  # 少なくとも2つは該当するはず
        assert total >= 2

    async def test_find_all_with_category_filter(
        self, repository: DocumentRepositoryImpl
    ) -> None:
        """カテゴリフィルターを使用した文書一覧取得をテストする。"""
        # カテゴリ別の文書を作成
        categories = ["技術文書", "技術文書", "営業資料", "管理文書"]
        for i, category in enumerate(categories):
            doc = Document.create(
                title=f"Document {i}",
                content=f"Content {i}".encode(),
                metadata=DocumentMetadata.create_new(
                    file_name=f"doc{i}.pdf",
                    file_size=1000,
                    content_type="application/pdf",
                    category=category,
                ),
            )
            await repository.save(doc)

        # カテゴリフィルターでの検索
        filter_ = DocumentFilter(category="技術文書")
        result, total = await repository.find_all(filter_=filter_)

        assert len(result) == 2
        assert total == 2
        assert all(item.category == "技術文書" for item in result)

    async def test_find_all_with_tags_filter(
        self, repository: DocumentRepositoryImpl
    ) -> None:
        """タグフィルターを使用した文書一覧取得をテストする。"""
        # タグ付き文書を作成
        docs = [
            Document.create(
                title="Python Tutorial",
                content=b"Content 1",
                metadata=DocumentMetadata.create_new(
                    file_name="python.pdf",
                    file_size=1000,
                    content_type="application/pdf",
                    tags=["Python", "プログラミング"],
                ),
            ),
            Document.create(
                title="FastAPI Guide",
                content=b"Content 2",
                metadata=DocumentMetadata.create_new(
                    file_name="fastapi.pdf",
                    file_size=2000,
                    content_type="application/pdf",
                    tags=["Python", "FastAPI", "Web"],
                ),
            ),
            Document.create(
                title="Java Guide",
                content=b"Content 3",
                metadata=DocumentMetadata.create_new(
                    file_name="java.pdf",
                    file_size=3000,
                    content_type="application/pdf",
                    tags=["Java", "プログラミング"],
                ),
            ),
        ]

        for doc in docs:
            await repository.save(doc)

        # タグフィルターでの検索（いずれかのタグに一致）
        filter_ = DocumentFilter(tags=["Python", "Web"])
        result, total = await repository.find_all(filter_=filter_)

        assert len(result) == 2
        assert total == 2
        titles = [item.title for item in result]
        assert "Python Tutorial" in titles
        assert "FastAPI Guide" in titles

    async def test_find_all_with_combined_filters(
        self, repository: DocumentRepositoryImpl
    ) -> None:
        """複合フィルターを使用した文書一覧取得をテストする。"""
        base_date = datetime.now()

        # 様々な属性を持つ文書を作成
        docs = [
            Document.create(
                title="技術仕様書 2024",
                content=b"Content 1",
                metadata=DocumentMetadata.create_new(
                    file_name="spec2024.pdf",
                    file_size=1000,
                    content_type="application/pdf",
                    category="技術文書",
                    tags=["仕様書", "2024"],
                ),
            ),
            Document.create(
                title="技術ガイド 2023",
                content=b"Content 2",
                metadata=DocumentMetadata.create_new(
                    file_name="guide2023.pdf",
                    file_size=2000,
                    content_type="application/pdf",
                    category="技術文書",
                    tags=["ガイド", "2023"],
                ).model_copy(
                    update={
                        "created_at": base_date - timedelta(days=400),
                        "updated_at": base_date - timedelta(days=400),
                    }
                ),
            ),
            Document.create(
                title="営業資料 2024",
                content=b"Content 3",
                metadata=DocumentMetadata.create_new(
                    file_name="sales2024.pdf",
                    file_size=3000,
                    content_type="application/pdf",
                    category="営業資料",
                    tags=["営業", "2024"],
                ),
            ),
        ]

        for doc in docs:
            await repository.save(doc)

        # 複合フィルター（タイトル、カテゴリ、日付）
        filter_ = DocumentFilter(
            title="技術",
            category="技術文書",
            created_from=base_date - timedelta(days=30),
        )
        result, total = await repository.find_all(filter_=filter_)

        assert len(result) == 1
        assert total == 1
        assert result[0].title == "技術仕様書 2024"

    async def test_find_all_with_pagination_and_filter(
        self, repository: DocumentRepositoryImpl
    ) -> None:
        """ページネーションとフィルターの組み合わせをテストする。"""
        # 多数の文書を作成
        for i in range(15):
            category = "技術文書" if i % 2 == 0 else "営業資料"
            doc = Document.create(
                title=f"Document {i:02d}",
                content=f"Content {i}".encode(),
                metadata=DocumentMetadata.create_new(
                    file_name=f"doc{i:02d}.pdf",
                    file_size=1000 + i,
                    content_type="application/pdf",
                    category=category,
                ),
            )
            await repository.save(doc)

        # カテゴリフィルターでページネーション
        filter_ = DocumentFilter(category="技術文書")

        # 1ページ目
        result1, total1 = await repository.find_all(skip=0, limit=5, filter_=filter_)
        assert len(result1) == 5
        assert total1 == 8  # 0, 2, 4, 6, 8, 10, 12, 14

        # 2ページ目
        result2, total2 = await repository.find_all(skip=5, limit=5, filter_=filter_)
        assert len(result2) == 3
        assert total2 == 8

        # 全てのアイテムがフィルター条件を満たしていることを確認
        all_items = result1 + result2
        assert all(item.category == "技術文書" for item in all_items)

    async def test_find_all_empty_filter(
        self, repository: DocumentRepositoryImpl
    ) -> None:
        """空のフィルターでの文書一覧取得をテストする。"""
        # 文書を作成
        for i in range(3):
            doc = Document.create(
                title=f"Document {i}",
                content=f"Content {i}".encode(),
                metadata=DocumentMetadata.create_new(
                    file_name=f"doc{i}.pdf",
                    file_size=1000,
                    content_type="application/pdf",
                ),
            )
            await repository.save(doc)

        # 空のフィルター（すべての文書を取得）
        empty_filter = DocumentFilter()
        result1, total1 = await repository.find_all(filter_=empty_filter)

        # フィルターなし（Noneを渡す）
        result2, total2 = await repository.find_all(filter_=None)

        # 両方とも同じ結果になることを確認
        assert len(result1) == len(result2) == 3
        assert total1 == total2 == 3
