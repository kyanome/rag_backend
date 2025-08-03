"""DeleteDocumentUseCaseのテスト。"""

import uuid
from unittest.mock import AsyncMock

import pytest

from src.application.use_cases.delete_document import (
    DeleteDocumentInput,
    DeleteDocumentUseCase,
)
from src.domain.exceptions.document_exceptions import DocumentNotFoundError
from src.domain.repositories import DocumentRepository
from src.domain.value_objects import DocumentId


@pytest.fixture
def mock_document_repository() -> AsyncMock:
    """モックの文書リポジトリを返す。"""
    return AsyncMock(spec=DocumentRepository)


@pytest.fixture
def delete_document_use_case(
    mock_document_repository: AsyncMock,
) -> DeleteDocumentUseCase:
    """DeleteDocumentUseCaseのインスタンスを返す。"""
    return DeleteDocumentUseCase(document_repository=mock_document_repository)


class TestDeleteDocumentUseCase:
    """DeleteDocumentUseCaseのテストクラス。"""

    @pytest.mark.anyio
    async def test_execute_success(
        self,
        delete_document_use_case: DeleteDocumentUseCase,
        mock_document_repository: AsyncMock,
    ) -> None:
        """文書の削除が正常に行われることを確認する。"""
        # Arrange
        document_id = str(uuid.uuid4())
        input_dto = DeleteDocumentInput(document_id=document_id)
        mock_document_repository.exists.return_value = True
        mock_document_repository.delete.return_value = None

        # Act
        await delete_document_use_case.execute(input_dto)

        # Assert
        mock_document_repository.exists.assert_called_once_with(
            DocumentId(value=document_id)
        )
        mock_document_repository.delete.assert_called_once_with(
            DocumentId(value=document_id)
        )

    @pytest.mark.anyio
    async def test_execute_document_not_found(
        self,
        delete_document_use_case: DeleteDocumentUseCase,
        mock_document_repository: AsyncMock,
    ) -> None:
        """文書が見つからない場合にDocumentNotFoundErrorが発生することを確認する。"""
        # Arrange
        document_id = str(uuid.uuid4())
        input_dto = DeleteDocumentInput(document_id=document_id)
        mock_document_repository.exists.return_value = False

        # Act & Assert
        with pytest.raises(DocumentNotFoundError) as exc_info:
            await delete_document_use_case.execute(input_dto)

        assert str(exc_info.value) == f"Document with id '{document_id}' not found"
        assert exc_info.value.document_id == document_id

        # deleteが呼ばれないことを確認
        mock_document_repository.delete.assert_not_called()

    @pytest.mark.anyio
    async def test_execute_repository_error_on_exists(
        self,
        delete_document_use_case: DeleteDocumentUseCase,
        mock_document_repository: AsyncMock,
    ) -> None:
        """存在確認時のリポジトリエラーが適切に処理されることを確認する。"""
        # Arrange
        document_id = str(uuid.uuid4())
        input_dto = DeleteDocumentInput(document_id=document_id)
        mock_document_repository.exists.side_effect = Exception("DB connection error")

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await delete_document_use_case.execute(input_dto)

        assert "Failed to delete document: DB connection error" in str(exc_info.value)

        # deleteが呼ばれないことを確認
        mock_document_repository.delete.assert_not_called()

    @pytest.mark.anyio
    async def test_execute_repository_error_on_delete(
        self,
        delete_document_use_case: DeleteDocumentUseCase,
        mock_document_repository: AsyncMock,
    ) -> None:
        """削除時のリポジトリエラーが適切に処理されることを確認する。"""
        # Arrange
        document_id = str(uuid.uuid4())
        input_dto = DeleteDocumentInput(document_id=document_id)
        mock_document_repository.exists.return_value = True
        mock_document_repository.delete.side_effect = Exception(
            "Delete operation failed"
        )

        # Act & Assert
        with pytest.raises(Exception) as exc_info:
            await delete_document_use_case.execute(input_dto)

        assert "Failed to delete document: Delete operation failed" in str(
            exc_info.value
        )

    @pytest.mark.anyio
    async def test_input_dto_validation(self) -> None:
        """入力DTOのバリデーションが正しく行われることを確認する。"""
        # Act & Assert - 正常なケース
        input_dto = DeleteDocumentInput(document_id="valid-id-123")
        assert input_dto.document_id == "valid-id-123"

        # 空文字列でも一応作成可能（DocumentIdのバリデーションで弾かれる）
        input_dto_empty = DeleteDocumentInput(document_id="")
        assert input_dto_empty.document_id == ""

    @pytest.mark.anyio
    async def test_execute_with_uuid_format_id(
        self,
        delete_document_use_case: DeleteDocumentUseCase,
        mock_document_repository: AsyncMock,
    ) -> None:
        """UUID形式のIDでも正常に削除できることを確認する。"""
        # Arrange
        uuid_id = "550e8400-e29b-41d4-a716-446655440000"
        input_dto = DeleteDocumentInput(document_id=uuid_id)
        mock_document_repository.exists.return_value = True
        mock_document_repository.delete.return_value = None

        # Act
        await delete_document_use_case.execute(input_dto)

        # Assert
        mock_document_repository.exists.assert_called_once_with(
            DocumentId(value=uuid_id)
        )
        mock_document_repository.delete.assert_called_once_with(
            DocumentId(value=uuid_id)
        )
