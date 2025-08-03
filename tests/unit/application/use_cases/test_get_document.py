"""GetDocumentUseCaseのテスト。"""

from unittest.mock import AsyncMock

import pytest

from src.application.use_cases.get_document import (
    GetDocumentInput,
    GetDocumentOutput,
    GetDocumentUseCase,
)
from src.domain.entities import Document
from src.domain.exceptions.document_exceptions import DocumentNotFoundError
from src.domain.repositories import DocumentRepository
from src.domain.value_objects import DocumentId, DocumentMetadata


@pytest.fixture
def mock_document_repository() -> AsyncMock:
    """モックの文書リポジトリを返す。"""
    return AsyncMock(spec=DocumentRepository)


@pytest.fixture
def get_document_use_case(mock_document_repository: AsyncMock) -> GetDocumentUseCase:
    """GetDocumentUseCaseのインスタンスを返す。"""
    return GetDocumentUseCase(document_repository=mock_document_repository)


@pytest.fixture
def sample_document() -> Document:
    """サンプルの文書エンティティを返す。"""
    import uuid
    from datetime import datetime

    metadata = DocumentMetadata(
        file_name="test.pdf",
        file_size=1024,
        content_type="application/pdf",
        category="技術文書",
        tags=["テスト", "サンプル"],
        author="テストユーザー",
        description="テスト用の文書です",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    return Document.create(
        title="テスト文書",
        content=b"test content",
        metadata=metadata,
        document_id=DocumentId(value=str(uuid.uuid4())),
    )


class TestGetDocumentUseCase:
    """GetDocumentUseCaseのテストクラス。"""

    @pytest.mark.anyio
    async def test_execute_success(
        self,
        get_document_use_case: GetDocumentUseCase,
        mock_document_repository: AsyncMock,
        sample_document: Document,
    ) -> None:
        """正常に文書を取得できることを確認する。"""
        # Arrange
        input_dto = GetDocumentInput(document_id=sample_document.id.value)
        mock_document_repository.find_by_id.return_value = sample_document

        # Act
        result = await get_document_use_case.execute(input_dto)

        # Assert
        assert isinstance(result, GetDocumentOutput)
        assert result.document_id == sample_document.id.value
        assert result.title == "テスト文書"
        assert result.file_name == "test.pdf"
        assert result.file_size == 1024
        assert result.content_type == "application/pdf"
        assert result.category == "技術文書"
        assert result.tags == ["テスト", "サンプル"]
        assert result.author == "テストユーザー"
        assert result.description == "テスト用の文書です"
        assert result.version == 1

        mock_document_repository.find_by_id.assert_called_once_with(
            DocumentId(value=sample_document.id.value)
        )

    @pytest.mark.anyio
    async def test_execute_document_not_found(
        self,
        get_document_use_case: GetDocumentUseCase,
        mock_document_repository: AsyncMock,
    ) -> None:
        """文書が見つからない場合にDocumentNotFoundErrorが発生することを確認する。"""
        # Arrange
        import uuid

        document_id = str(uuid.uuid4())
        input_dto = GetDocumentInput(document_id=document_id)
        mock_document_repository.find_by_id.return_value = None

        # Act & Assert
        with pytest.raises(DocumentNotFoundError) as exc_info:
            await get_document_use_case.execute(input_dto)

        assert str(exc_info.value) == f"Document with id '{document_id}' not found"
        assert exc_info.value.document_id == document_id

    @pytest.mark.anyio
    async def test_execute_repository_error(
        self,
        get_document_use_case: GetDocumentUseCase,
        mock_document_repository: AsyncMock,
    ) -> None:
        """リポジトリエラーが適切に処理されることを確認する。"""
        # Arrange
        import uuid

        document_id = str(uuid.uuid4())
        input_dto = GetDocumentInput(document_id=document_id)
        mock_document_repository.find_by_id.side_effect = Exception(
            "DB connection error"
        )

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await get_document_use_case.execute(input_dto)

        assert "Failed to get document: DB connection error" in str(exc_info.value)

    @pytest.mark.anyio
    async def test_from_domain_conversion(
        self,
        sample_document: Document,
    ) -> None:
        """ドメインモデルから出力DTOへの変換が正しく行われることを確認する。"""
        # Act
        output = GetDocumentOutput.from_domain(sample_document)

        # Assert
        assert output.document_id == sample_document.id.value
        assert output.title == "テスト文書"
        assert output.file_name == "test.pdf"
        assert output.file_size == 1024
        assert output.content_type == "application/pdf"
        assert output.category == "技術文書"
        assert output.tags == ["テスト", "サンプル"]
        assert output.author == "テストユーザー"
        assert output.description == "テスト用の文書です"
        assert output.version == 1

    @pytest.mark.anyio
    async def test_execute_with_minimal_metadata(
        self,
        get_document_use_case: GetDocumentUseCase,
        mock_document_repository: AsyncMock,
    ) -> None:
        """最小限のメタデータの文書でも正常に取得できることを確認する。"""
        # Arrange
        import uuid
        from datetime import datetime

        metadata = DocumentMetadata(
            file_name="minimal.txt",
            file_size=100,
            content_type="text/plain",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        document = Document.create(
            title="最小文書",
            content=b"minimal content",
            metadata=metadata,
            document_id=DocumentId(value=str(uuid.uuid4())),
        )

        input_dto = GetDocumentInput(document_id=document.id.value)
        mock_document_repository.find_by_id.return_value = document

        # Act
        result = await get_document_use_case.execute(input_dto)

        # Assert
        assert result.document_id == document.id.value
        assert result.title == "最小文書"
        assert result.file_name == "minimal.txt"
        assert result.file_size == 100
        assert result.content_type == "text/plain"
        assert result.category is None
        assert result.tags == []
        assert result.author is None
        assert result.description is None
