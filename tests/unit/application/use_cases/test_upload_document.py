"""文書アップロードユースケースのテスト。"""

from unittest.mock import AsyncMock, Mock

import pytest

from src.application.use_cases.chunk_document import ChunkDocumentOutput
from src.application.use_cases.upload_document import (
    UploadDocumentInput,
    UploadDocumentUseCase,
)
from src.domain.entities import Document


class TestUploadDocumentUseCase:
    """UploadDocumentUseCaseのテスト。"""

    @pytest.fixture
    def mock_document_repository(self) -> AsyncMock:
        """モックの文書リポジトリ。"""
        return AsyncMock()

    @pytest.fixture
    def mock_file_storage_service(self) -> AsyncMock:
        """モックのファイルストレージサービス。"""
        mock = AsyncMock()
        mock.save = AsyncMock(return_value="path/to/file.pdf")
        return mock

    @pytest.fixture
    def mock_chunk_document_use_case(self) -> Mock:
        """モックのチャンク化ユースケース。"""
        mock = Mock()
        chunk_output = ChunkDocumentOutput(
            document_id="test-doc-id",
            chunk_count=5,
            total_characters=1000,
            status="success",
        )
        mock.execute = AsyncMock(return_value=chunk_output)
        return mock

    @pytest.fixture
    def use_case(
        self,
        mock_document_repository: AsyncMock,
        mock_file_storage_service: AsyncMock,
    ) -> UploadDocumentUseCase:
        """テスト用のユースケース（チャンク化なし）。"""
        return UploadDocumentUseCase(
            document_repository=mock_document_repository,
            file_storage_service=mock_file_storage_service,
        )

    @pytest.fixture
    def use_case_with_chunking(
        self,
        mock_document_repository: AsyncMock,
        mock_file_storage_service: AsyncMock,
        mock_chunk_document_use_case: Mock,
    ) -> UploadDocumentUseCase:
        """テスト用のユースケース（チャンク化あり）。"""
        return UploadDocumentUseCase(
            document_repository=mock_document_repository,
            file_storage_service=mock_file_storage_service,
            chunk_document_use_case=mock_chunk_document_use_case,
        )

    @pytest.fixture
    def valid_input(self) -> UploadDocumentInput:
        """有効な入力データ。"""
        return UploadDocumentInput(
            file_name="test.pdf",
            file_content=b"test content",
            file_size=len(b"test content"),
            content_type="application/pdf",
            title="Test Document",
            category="Test Category",
            tags=["tag1", "tag2"],
            author="Test Author",
            description="Test Description",
        )

    async def test_execute_with_valid_input(
        self,
        use_case: UploadDocumentUseCase,
        valid_input: UploadDocumentInput,
        mock_document_repository: AsyncMock,
        mock_file_storage_service: AsyncMock,
    ) -> None:
        """有効な入力でユースケースを実行できる。"""
        # 実行
        result = await use_case.execute(valid_input)

        # 検証
        assert result.title == "Test Document"
        assert result.file_name == "test.pdf"
        assert result.file_size == len(b"test content")
        assert result.content_type == "application/pdf"
        assert result.document_id

        # ファイル保存が呼ばれたことを確認
        mock_file_storage_service.save.assert_called_once()
        save_call = mock_file_storage_service.save.call_args
        assert save_call[1]["file_name"] == "test.pdf"
        assert save_call[1]["content"] == b"test content"

        # リポジトリ保存が呼ばれたことを確認
        mock_document_repository.save.assert_called_once()
        saved_document = mock_document_repository.save.call_args[0][0]
        assert isinstance(saved_document, Document)
        assert saved_document.title == "Test Document"

    async def test_execute_with_minimal_input(
        self,
        use_case: UploadDocumentUseCase,
        mock_document_repository: AsyncMock,
        mock_file_storage_service: AsyncMock,
    ) -> None:
        """最小限の入力でユースケースを実行できる。"""
        # 入力データ
        input_dto = UploadDocumentInput(
            file_name="minimal.txt",
            file_content=b"minimal content",
            file_size=len(b"minimal content"),
            content_type="text/plain",
        )

        # 実行
        result = await use_case.execute(input_dto)

        # 検証
        assert result.title == "minimal.txt"  # タイトルはファイル名になる
        assert result.file_name == "minimal.txt"
        assert result.content_type == "text/plain"

    async def test_execute_with_file_size_exceeding_limit(
        self,
        use_case: UploadDocumentUseCase,
    ) -> None:
        """ファイルサイズが制限を超える場合はエラー。"""
        # 入力データ（100MB + 1バイト）
        input_dto = UploadDocumentInput(
            file_name="large.pdf",
            file_content=b"x",
            file_size=100 * 1024 * 1024 + 1,
            content_type="application/pdf",
        )

        # 実行と検証
        with pytest.raises(ValueError, match="exceeds maximum allowed size"):
            await use_case.execute(input_dto)

    async def test_execute_with_unsupported_content_type(
        self,
        use_case: UploadDocumentUseCase,
    ) -> None:
        """サポートされていないコンテンツタイプの場合はエラー。"""
        # 入力データ
        input_dto = UploadDocumentInput(
            file_name="test.exe",
            file_content=b"executable",
            file_size=len(b"executable"),
            content_type="application/x-msdownload",
        )

        # 実行と検証
        with pytest.raises(ValueError, match="Unsupported content type"):
            await use_case.execute(input_dto)

    async def test_execute_with_empty_file_name(
        self,
        use_case: UploadDocumentUseCase,
    ) -> None:
        """ファイル名が空の場合はエラー。"""
        # 入力データ
        input_dto = UploadDocumentInput(
            file_name="",
            file_content=b"content",
            file_size=len(b"content"),
            content_type="text/plain",
        )

        # 実行と検証
        with pytest.raises(ValueError, match="File name cannot be empty"):
            await use_case.execute(input_dto)

    async def test_execute_with_empty_file_content(
        self,
        use_case: UploadDocumentUseCase,
    ) -> None:
        """ファイル内容が空の場合はエラー。"""
        # 入力データ
        input_dto = UploadDocumentInput(
            file_name="empty.txt",
            file_content=b"",
            file_size=0,
            content_type="text/plain",
        )

        # 実行と検証
        with pytest.raises(ValueError, match="File content cannot be empty"):
            await use_case.execute(input_dto)

    async def test_supported_content_types(
        self,
        use_case: UploadDocumentUseCase,
    ) -> None:
        """サポートされているコンテンツタイプを確認。"""
        expected_types = {
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
            "text/plain",
            "text/csv",
            "text/markdown",
        }
        assert use_case.SUPPORTED_CONTENT_TYPES == expected_types

    def test_max_file_size(
        self,
        use_case: UploadDocumentUseCase,
    ) -> None:
        """最大ファイルサイズが100MBであることを確認。"""
        assert use_case.MAX_FILE_SIZE == 100 * 1024 * 1024

    async def test_execute_with_chunking_enabled(
        self,
        use_case_with_chunking: UploadDocumentUseCase,
        valid_input: UploadDocumentInput,
        mock_document_repository: AsyncMock,
        mock_file_storage_service: AsyncMock,
        mock_chunk_document_use_case: Mock,
    ) -> None:
        """チャンク化が有効な場合の処理を確認。"""
        # 実行
        result = await use_case_with_chunking.execute(valid_input)

        # 検証
        assert result.title == "Test Document"
        assert result.chunk_count == 5
        assert result.chunking_status == "success"

        # チャンク化が呼ばれたことを確認
        mock_chunk_document_use_case.execute.assert_called_once()

    async def test_execute_with_chunking_failure(
        self,
        use_case_with_chunking: UploadDocumentUseCase,
        valid_input: UploadDocumentInput,
        mock_document_repository: AsyncMock,
        mock_file_storage_service: AsyncMock,
        mock_chunk_document_use_case: Mock,
    ) -> None:
        """チャンク化が失敗しても文書アップロードは成功することを確認。"""
        # チャンク化をエラーにする
        mock_chunk_document_use_case.execute = AsyncMock(
            side_effect=Exception("Chunking failed")
        )

        # 実行
        result = await use_case_with_chunking.execute(valid_input)

        # 検証 - アップロードは成功
        assert result.title == "Test Document"
        assert result.chunk_count == 0
        assert result.chunking_status == "failed"

        # 文書は保存されている
        mock_document_repository.save.assert_called_once()
