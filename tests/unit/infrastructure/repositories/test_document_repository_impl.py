"""DocumentRepositoryImplのテスト。"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities import Document
from src.domain.exceptions import DocumentNotFoundError
from src.domain.value_objects import DocumentId, DocumentMetadata
from src.infrastructure.database.models import DocumentModel
from src.infrastructure.externals.file_storage import FileStorageService
from src.infrastructure.repositories.document_repository_impl import (
    DocumentRepositoryImpl,
)


@pytest.fixture
def mock_session() -> AsyncMock:
    """モックのデータベースセッションを作成する。"""
    session = AsyncMock(spec=AsyncSession)
    return session


@pytest.fixture
def mock_file_storage() -> AsyncMock:
    """モックのファイルストレージサービスを作成する。"""
    storage = AsyncMock(spec=FileStorageService)
    return storage


@pytest.fixture
def repository(
    mock_session: AsyncMock, mock_file_storage: AsyncMock
) -> DocumentRepositoryImpl:
    """テスト用のリポジトリインスタンスを作成する。"""
    return DocumentRepositoryImpl(session=mock_session, file_storage=mock_file_storage)


@pytest.fixture
def sample_document() -> Document:
    """テスト用のドキュメントを作成する。"""
    metadata = DocumentMetadata.create_new(
        file_name="test.pdf",
        file_size=1024,
        content_type="application/pdf",
        category="テスト",
        tags=["サンプル"],
    )
    return Document.create(
        title="テスト文書",
        content=b"Test content",
        metadata=metadata,
    )


class TestDocumentRepositoryImpl:
    """DocumentRepositoryImplのテストクラス。"""

    async def test_save_new_document(
        self,
        repository: DocumentRepositoryImpl,
        mock_session: AsyncMock,
        mock_file_storage: AsyncMock,
        sample_document: Document,
    ) -> None:
        """新規文書の保存をテストする。"""
        mock_session.get.return_value = None
        mock_file_storage.save.return_value = "test/path/test.pdf"

        await repository.save(sample_document)

        mock_file_storage.save.assert_called_once_with(
            document_id=sample_document.id.value,
            file_name=sample_document.metadata.file_name,
            content=sample_document.content,
        )
        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()

    async def test_save_existing_document(
        self,
        repository: DocumentRepositoryImpl,
        mock_session: AsyncMock,
        mock_file_storage: AsyncMock,
        sample_document: Document,
    ) -> None:
        """既存文書の更新をテストする。"""
        existing_model = MagicMock(spec=DocumentModel)
        existing_model.chunks = []
        mock_session.get.return_value = existing_model
        mock_file_storage.save.return_value = "test/path/test.pdf"

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await repository.save(sample_document)

        assert existing_model.title == sample_document.title
        assert existing_model.version == sample_document.version
        mock_session.commit.assert_called_once()

    async def test_save_rollback_on_error(
        self,
        repository: DocumentRepositoryImpl,
        mock_session: AsyncMock,
        mock_file_storage: AsyncMock,
        sample_document: Document,
    ) -> None:
        """保存エラー時のロールバックをテストする。"""
        mock_session.get.side_effect = Exception("Database error")

        with pytest.raises(Exception, match="Failed to save document"):
            await repository.save(sample_document)

        mock_session.rollback.assert_called_once()

    async def test_find_by_id_found(
        self,
        repository: DocumentRepositoryImpl,
        mock_session: AsyncMock,
        sample_document: Document,
    ) -> None:
        """IDによる文書検索（見つかる場合）をテストする。"""
        mock_model = MagicMock(spec=DocumentModel)
        mock_model.to_domain.return_value = sample_document

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_model
        mock_session.execute.return_value = mock_result

        result = await repository.find_by_id(sample_document.id)

        assert result == sample_document

    async def test_find_by_id_not_found(
        self,
        repository: DocumentRepositoryImpl,
        mock_session: AsyncMock,
    ) -> None:
        """IDによる文書検索（見つからない場合）をテストする。"""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        document_id = DocumentId.generate()
        result = await repository.find_by_id(document_id)

        assert result is None

    async def test_find_all(
        self,
        repository: DocumentRepositoryImpl,
        mock_session: AsyncMock,
        sample_document: Document,
    ) -> None:
        """全文書の取得をテストする。"""
        mock_model = MagicMock(spec=DocumentModel)
        mock_model.to_domain.return_value = sample_document

        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 1

        mock_docs_result = MagicMock()
        mock_docs_result.scalars.return_value.all.return_value = [mock_model]

        mock_session.execute.side_effect = [mock_count_result, mock_docs_result]

        documents, total = await repository.find_all(skip=0, limit=10)

        assert len(documents) == 1
        assert total == 1
        assert documents[0] == sample_document

    async def test_update(
        self,
        repository: DocumentRepositoryImpl,
        sample_document: Document,
    ) -> None:
        """文書の更新をテストする。"""
        with patch.object(
            repository, "find_by_id", return_value=sample_document
        ) as mock_find:
            with patch.object(repository, "save") as mock_save:
                await repository.update(sample_document)

                mock_find.assert_called_once_with(sample_document.id)
                mock_save.assert_called_once()
                assert sample_document.version == 2

    async def test_update_not_found(
        self,
        repository: DocumentRepositoryImpl,
        sample_document: Document,
    ) -> None:
        """存在しない文書の更新をテストする。"""
        with patch.object(repository, "find_by_id", return_value=None):
            with pytest.raises(DocumentNotFoundError):
                await repository.update(sample_document)

    async def test_delete(
        self,
        repository: DocumentRepositoryImpl,
        mock_session: AsyncMock,
        mock_file_storage: AsyncMock,
    ) -> None:
        """文書の削除をテストする。"""
        document_id = DocumentId.generate()
        mock_model = MagicMock(spec=DocumentModel)
        mock_model.file_path = "test/path/test.pdf"
        mock_session.get.return_value = mock_model

        await repository.delete(document_id)

        mock_file_storage.delete.assert_called_once_with("test/path/test.pdf")
        mock_session.delete.assert_called_once_with(mock_model)
        mock_session.commit.assert_called_once()

    async def test_delete_not_found(
        self,
        repository: DocumentRepositoryImpl,
        mock_session: AsyncMock,
    ) -> None:
        """存在しない文書の削除をテストする。"""
        document_id = DocumentId.generate()
        mock_session.get.return_value = None

        with pytest.raises(DocumentNotFoundError):
            await repository.delete(document_id)

    async def test_delete_file_not_found_ignored(
        self,
        repository: DocumentRepositoryImpl,
        mock_session: AsyncMock,
        mock_file_storage: AsyncMock,
    ) -> None:
        """ファイルが存在しない場合の削除をテストする。"""
        document_id = DocumentId.generate()
        mock_model = MagicMock(spec=DocumentModel)
        mock_model.file_path = "test/path/test.pdf"
        mock_session.get.return_value = mock_model
        mock_file_storage.delete.side_effect = FileNotFoundError()

        await repository.delete(document_id)

        mock_session.delete.assert_called_once_with(mock_model)
        mock_session.commit.assert_called_once()

    async def test_exists_true(
        self,
        repository: DocumentRepositoryImpl,
        mock_session: AsyncMock,
    ) -> None:
        """文書の存在確認（存在する場合）をテストする。"""
        document_id = DocumentId.generate()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = uuid.uuid4()
        mock_session.execute.return_value = mock_result

        result = await repository.exists(document_id)

        assert result is True

    async def test_exists_false(
        self,
        repository: DocumentRepositoryImpl,
        mock_session: AsyncMock,
    ) -> None:
        """文書の存在確認（存在しない場合）をテストする。"""
        document_id = DocumentId.generate()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        result = await repository.exists(document_id)

        assert result is False

    async def test_find_by_title(
        self,
        repository: DocumentRepositoryImpl,
        mock_session: AsyncMock,
        sample_document: Document,
    ) -> None:
        """タイトルによる文書検索をテストする。"""
        mock_model = MagicMock(spec=DocumentModel)
        mock_model.to_domain.return_value = sample_document

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_model]
        mock_session.execute.return_value = mock_result

        results = await repository.find_by_title("テスト")

        assert len(results) == 1
        assert results[0] == sample_document
