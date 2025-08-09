"""ChunkDocumentUseCaseのテスト。"""

from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from src.application.use_cases import ChunkDocumentInput, ChunkDocumentOutput, ChunkDocumentUseCase
from src.domain.entities import Document
from src.domain.externals import ChunkingStrategy, ExtractedText, TextExtractor
from src.domain.repositories import DocumentRepository
from src.domain.services import ChunkingService
from src.domain.value_objects import DocumentChunk, DocumentId, DocumentMetadata


class TestChunkDocumentUseCase:
    """ChunkDocumentUseCaseのテスト。"""

    @pytest.fixture
    def mock_repository(self) -> Mock:
        """モックリポジトリを作成する。"""
        return Mock(spec=DocumentRepository)

    @pytest.fixture
    def mock_text_extractor(self) -> Mock:
        """モックテキスト抽出器を作成する。"""
        return Mock(spec=TextExtractor)

    @pytest.fixture
    def mock_chunking_strategy(self) -> Mock:
        """モックチャンク分割戦略を作成する。"""
        return Mock(spec=ChunkingStrategy)

    @pytest.fixture
    def chunking_service(self) -> ChunkingService:
        """ChunkingServiceインスタンスを作成する。"""
        return ChunkingService()

    @pytest.fixture
    def use_case(
        self,
        mock_repository: Mock,
        mock_text_extractor: Mock,
        mock_chunking_strategy: Mock,
        chunking_service: ChunkingService,
    ) -> ChunkDocumentUseCase:
        """ChunkDocumentUseCaseインスタンスを作成する。"""
        return ChunkDocumentUseCase(
            document_repository=mock_repository,
            text_extractor=mock_text_extractor,
            chunking_strategy=mock_chunking_strategy,
            chunking_service=chunking_service,
        )

    @pytest.fixture
    def sample_document(self) -> Document:
        """サンプル文書を作成する。"""
        metadata = DocumentMetadata.create_new(
            file_name="test.pdf",
            file_size=1000,
            content_type="application/pdf",
        )
        return Document.create(
            title="Test Document",
            content=b"PDF content bytes",
            metadata=metadata,
        )

    @pytest.mark.asyncio
    async def test_execute_success(
        self,
        use_case: ChunkDocumentUseCase,
        mock_repository: Mock,
        mock_text_extractor: Mock,
        mock_chunking_strategy: Mock,
        sample_document: Document,
    ) -> None:
        """正常にチャンク化が実行されることを確認する。"""
        # Arrange
        input_dto = ChunkDocumentInput(
            document_id="test-doc-id",
            chunk_size=100,
            overlap_size=20,
        )
        
        mock_repository.find_by_id = AsyncMock(return_value=sample_document)
        mock_repository.save = AsyncMock()
        
        extracted_text = ExtractedText(
            content="This is a test document content.",
            metadata={"page_count": 1}
        )
        mock_text_extractor.extract_text = AsyncMock(return_value=extracted_text)
        
        # チャンク分割戦略のモック
        mock_chunking_strategy.split_text.return_value = [
            ("This is a test", 0, 14),
            ("test document content.", 10, 32),
        ]
        
        # Act
        result = await use_case.execute(input_dto)
        
        # Assert
        assert isinstance(result, ChunkDocumentOutput)
        assert result.document_id == "test-doc-id"
        assert result.chunk_count == 2
        assert result.total_characters == len(extracted_text.content)
        assert result.status == "success"
        
        mock_repository.find_by_id.assert_called_once()
        mock_text_extractor.extract_text.assert_called_once_with(
            content=sample_document.content,
            content_type=sample_document.metadata.content_type,
        )
        mock_repository.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_document_not_found(
        self,
        use_case: ChunkDocumentUseCase,
        mock_repository: Mock,
    ) -> None:
        """文書が見つからない場合にエラーが発生することを確認する。"""
        # Arrange
        input_dto = ChunkDocumentInput(document_id="non-existent-id")
        mock_repository.find_by_id = AsyncMock(return_value=None)
        
        # Act & Assert
        with pytest.raises(ValueError, match="Document not found"):
            await use_case.execute(input_dto)

    @pytest.mark.asyncio
    async def test_execute_empty_text(
        self,
        use_case: ChunkDocumentUseCase,
        mock_repository: Mock,
        mock_text_extractor: Mock,
        sample_document: Document,
    ) -> None:
        """空のテキストの場合の処理を確認する。"""
        # Arrange
        input_dto = ChunkDocumentInput(document_id="test-doc-id")
        
        mock_repository.find_by_id = AsyncMock(return_value=sample_document)
        
        # 空のテキストを返す
        empty_text = ExtractedText(content="", metadata={})
        mock_text_extractor.extract_text = AsyncMock(return_value=empty_text)
        
        # Act
        result = await use_case.execute(input_dto)
        
        # Assert
        assert result.chunk_count == 0
        assert result.total_characters == 0
        assert result.status == "success"

    @pytest.mark.asyncio
    async def test_execute_extraction_error(
        self,
        use_case: ChunkDocumentUseCase,
        mock_repository: Mock,
        mock_text_extractor: Mock,
        sample_document: Document,
    ) -> None:
        """テキスト抽出でエラーが発生した場合の処理を確認する。"""
        # Arrange
        input_dto = ChunkDocumentInput(document_id="test-doc-id")
        
        mock_repository.find_by_id = AsyncMock(return_value=sample_document)
        mock_text_extractor.extract_text = AsyncMock(
            side_effect=Exception("Extraction failed")
        )
        
        # Act
        result = await use_case.execute(input_dto)
        
        # Assert
        assert result.chunk_count == 0
        assert result.total_characters == 0
        assert result.status == "failed"

    @pytest.mark.asyncio
    async def test_execute_with_custom_parameters(
        self,
        use_case: ChunkDocumentUseCase,
        mock_repository: Mock,
        mock_text_extractor: Mock,
        mock_chunking_strategy: Mock,
        sample_document: Document,
    ) -> None:
        """カスタムパラメータでチャンク化が実行されることを確認する。"""
        # Arrange
        input_dto = ChunkDocumentInput(
            document_id="test-doc-id",
            chunk_size=500,
            overlap_size=50,
        )
        
        mock_repository.find_by_id = AsyncMock(return_value=sample_document)
        mock_repository.save = AsyncMock()
        
        extracted_text = ExtractedText(
            content="Long document content " * 100,
            metadata={}
        )
        mock_text_extractor.extract_text = AsyncMock(return_value=extracted_text)
        
        # より多くのチャンクを返す
        mock_chunking_strategy.split_text.return_value = [
            (f"Chunk {i}", i * 450, (i + 1) * 450)
            for i in range(5)
        ]
        
        # Act
        result = await use_case.execute(input_dto)
        
        # Assert
        assert result.chunk_count == 5
        assert result.status == "success"
        
        # カスタムパラメータが渡されていることを確認
        mock_chunking_strategy.split_text.assert_called_once()
        call_args = mock_chunking_strategy.split_text.call_args
        assert call_args[0][1] == 500  # chunk_size
        assert call_args[0][2] == 50   # overlap_size