"""UpdateDocumentUseCaseのテスト。"""

from unittest.mock import AsyncMock

import pytest

from src.application.use_cases.update_document import (
    UpdateDocumentInput,
    UpdateDocumentOutput,
    UpdateDocumentUseCase,
)
from src.domain.entities import Document
from src.domain.exceptions.document_exceptions import (
    DocumentNotFoundError,
    DocumentValidationError,
)
from src.domain.repositories import DocumentRepository
from src.domain.value_objects import DocumentId, DocumentMetadata


@pytest.fixture
def mock_document_repository() -> AsyncMock:
    """モックの文書リポジトリを返す。"""
    return AsyncMock(spec=DocumentRepository)


@pytest.fixture
def update_document_use_case(
    mock_document_repository: AsyncMock,
) -> UpdateDocumentUseCase:
    """UpdateDocumentUseCaseのインスタンスを返す。"""
    return UpdateDocumentUseCase(document_repository=mock_document_repository)


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


class TestUpdateDocumentUseCase:
    """UpdateDocumentUseCaseのテストクラス。"""

    @pytest.mark.anyio
    async def test_execute_update_title_success(
        self,
        update_document_use_case: UpdateDocumentUseCase,
        mock_document_repository: AsyncMock,
        sample_document: Document,
    ) -> None:
        """タイトルの更新が正常に行われることを確認する。"""
        # Arrange
        input_dto = UpdateDocumentInput(
            document_id=sample_document.id.value,
            title="更新されたタイトル",
        )

        # 更新後の文書
        updated_document = sample_document.model_copy()
        updated_document.title = "更新されたタイトル"
        updated_document.version = 2

        mock_document_repository.find_by_id.side_effect = [
            sample_document,  # 最初の取得
            updated_document,  # 更新後の取得
        ]
        mock_document_repository.update.return_value = None

        # Act
        result = await update_document_use_case.execute(input_dto)

        # Assert
        assert isinstance(result, UpdateDocumentOutput)
        assert result.document_id == sample_document.id.value
        assert result.title == "更新されたタイトル"
        assert result.version == 2

        # リポジトリメソッドの呼び出し確認
        assert mock_document_repository.find_by_id.call_count == 2
        mock_document_repository.update.assert_called_once()

    @pytest.mark.anyio
    async def test_execute_update_metadata_success(
        self,
        update_document_use_case: UpdateDocumentUseCase,
        mock_document_repository: AsyncMock,
        sample_document: Document,
    ) -> None:
        """メタデータの更新が正常に行われることを確認する。"""
        # Arrange
        input_dto = UpdateDocumentInput(
            document_id=sample_document.id.value,
            category="更新カテゴリ",
            tags=["新タグ1", "新タグ2"],
            author="更新ユーザー",
            description="更新された説明",
        )

        # 更新後の文書
        updated_document = sample_document.model_copy()
        updated_document.metadata = updated_document.metadata.model_copy(
            update={
                "category": "更新カテゴリ",
                "tags": ["新タグ1", "新タグ2"],
                "author": "更新ユーザー",
                "description": "更新された説明",
            }
        )
        updated_document.version = 2

        mock_document_repository.find_by_id.side_effect = [
            sample_document,
            updated_document,
        ]
        mock_document_repository.update.return_value = None

        # Act
        result = await update_document_use_case.execute(input_dto)

        # Assert
        assert result.category == "更新カテゴリ"
        assert result.tags == ["新タグ1", "新タグ2"]
        assert result.author == "更新ユーザー"
        assert result.description == "更新された説明"
        assert result.version == 2

    @pytest.mark.anyio
    async def test_execute_document_not_found(
        self,
        update_document_use_case: UpdateDocumentUseCase,
        mock_document_repository: AsyncMock,
    ) -> None:
        """文書が見つからない場合にDocumentNotFoundErrorが発生することを確認する。"""
        # Arrange
        import uuid

        document_id = str(uuid.uuid4())
        input_dto = UpdateDocumentInput(
            document_id=document_id,
            title="新しいタイトル",
        )
        mock_document_repository.find_by_id.return_value = None

        # Act & Assert
        with pytest.raises(DocumentNotFoundError) as exc_info:
            await update_document_use_case.execute(input_dto)

        assert str(exc_info.value) == f"Document with id '{document_id}' not found"

    @pytest.mark.anyio
    async def test_execute_no_update_fields(
        self,
        update_document_use_case: UpdateDocumentUseCase,
    ) -> None:
        """更新フィールドが指定されていない場合にValueErrorが発生することを確認する。"""
        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            UpdateDocumentInput(document_id="test-id-123")

        assert "At least one field must be provided for update" in str(exc_info.value)

    @pytest.mark.anyio
    async def test_execute_invalid_title(
        self,
        update_document_use_case: UpdateDocumentUseCase,
        mock_document_repository: AsyncMock,
        sample_document: Document,
    ) -> None:
        """無効なタイトルの場合にDocumentValidationErrorが発生することを確認する。"""
        # Arrange
        input_dto = UpdateDocumentInput(
            document_id=sample_document.id.value,
            title="   ",  # 空白のみのタイトル
        )
        mock_document_repository.find_by_id.return_value = sample_document

        # Act & Assert
        with pytest.raises(DocumentValidationError) as exc_info:
            await update_document_use_case.execute(input_dto)

        assert exc_info.value.field == "title"
        assert "Title cannot be empty" in exc_info.value.message

    @pytest.mark.anyio
    async def test_execute_repository_error(
        self,
        update_document_use_case: UpdateDocumentUseCase,
        mock_document_repository: AsyncMock,
        sample_document: Document,
    ) -> None:
        """リポジトリエラーが適切に処理されることを確認する。"""
        # Arrange
        input_dto = UpdateDocumentInput(
            document_id=sample_document.id.value,
            title="新しいタイトル",
        )
        mock_document_repository.find_by_id.return_value = sample_document
        mock_document_repository.update.side_effect = Exception("DB connection error")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await update_document_use_case.execute(input_dto)

        assert "Failed to update document: DB connection error" in str(exc_info.value)

    @pytest.mark.anyio
    async def test_execute_partial_update(
        self,
        update_document_use_case: UpdateDocumentUseCase,
        mock_document_repository: AsyncMock,
        sample_document: Document,
    ) -> None:
        """一部のフィールドのみの更新が正常に行われることを確認する。"""
        # Arrange
        input_dto = UpdateDocumentInput(
            document_id=sample_document.id.value,
            tags=["新タグ"],  # タグのみ更新
        )

        # 更新後の文書（タグのみ変更）
        updated_document = sample_document.model_copy()
        updated_document.metadata = updated_document.metadata.model_copy(
            update={"tags": ["新タグ"]}
        )
        updated_document.version = 2

        mock_document_repository.find_by_id.side_effect = [
            sample_document,
            updated_document,
        ]
        mock_document_repository.update.return_value = None

        # Act
        result = await update_document_use_case.execute(input_dto)

        # Assert
        assert result.title == "テスト文書"  # 変更されていない
        assert result.category == "技術文書"  # 変更されていない
        assert result.tags == ["新タグ"]  # 更新された
        assert result.author == "テストユーザー"  # 変更されていない
        assert result.version == 2

    @pytest.mark.anyio
    async def test_from_domain_conversion(
        self,
        sample_document: Document,
    ) -> None:
        """ドメインモデルから出力DTOへの変換が正しく行われることを確認する。"""
        # Act
        output = UpdateDocumentOutput.from_domain(sample_document)

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
