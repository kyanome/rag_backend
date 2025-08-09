"""埋め込み生成ユースケースの単体テスト。"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from src.application.use_cases.generate_embeddings import (
    GenerateEmbeddingsInput,
    GenerateEmbeddingsUseCase,
)
from src.domain.entities import Document
from src.domain.externals import EmbeddingResult, EmbeddingService
from src.domain.repositories import DocumentRepository
from src.domain.value_objects import (
    ChunkMetadata,
    DocumentChunk,
    DocumentId,
    DocumentMetadata,
)


class TestGenerateEmbeddingsUseCase:
    """GenerateEmbeddingsUseCaseのテスト。"""

    @pytest.fixture
    def mock_repository(self) -> Mock:
        """モックリポジトリを作成する。"""
        return Mock(spec=DocumentRepository)

    @pytest.fixture
    def mock_embedding_service(self) -> Mock:
        """モック埋め込みサービスを作成する。"""
        service = Mock(spec=EmbeddingService)
        service.get_model_name.return_value = "test-model"
        service.get_dimensions.return_value = 384
        return service

    @pytest.fixture
    def use_case(
        self, mock_repository: Mock, mock_embedding_service: Mock
    ) -> GenerateEmbeddingsUseCase:
        """テスト用のユースケースを作成する。"""
        return GenerateEmbeddingsUseCase(
            document_repository=mock_repository,
            embedding_service=mock_embedding_service,
        )

    @pytest.fixture
    def sample_document(self) -> Document:
        """サンプル文書を作成する。"""
        doc_id = DocumentId(value="123e4567-e89b-12d3-a456-426614174000")
        chunks = [
            DocumentChunk(
                id=f"chunk-{i}",
                document_id=doc_id,
                content=f"Chunk content {i}",
                embedding=None,
                metadata=ChunkMetadata(
                    chunk_index=i,
                    start_position=i * 100,
                    end_position=(i + 1) * 100,
                    total_chunks=3,
                ),
            )
            for i in range(3)
        ]

        return Document(
            id=doc_id,
            title="Test Document",
            content=b"Test content",
            metadata=DocumentMetadata(
                file_name="test.txt",
                file_size=1000,
                content_type="text/plain",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            ),
            chunks=chunks,
            version=1,
        )

    @pytest.mark.asyncio
    async def test_execute_success(
        self,
        use_case: GenerateEmbeddingsUseCase,
        mock_repository: Mock,
        mock_embedding_service: Mock,
        sample_document: Document,
    ) -> None:
        """正常に埋め込みを生成できることを確認する。"""
        # セットアップ
        mock_repository.find_by_id = AsyncMock(return_value=sample_document)
        mock_repository.save = AsyncMock()

        embedding_results = [
            EmbeddingResult(
                embedding=[float(i)] * 384,
                model="test-model",
                dimensions=384,
            )
            for i in range(3)
        ]
        mock_embedding_service.generate_batch_embeddings = AsyncMock(
            return_value=embedding_results
        )

        # 実行
        input_dto = GenerateEmbeddingsInput(
            document_id="123e4567-e89b-12d3-a456-426614174000"
        )
        output = await use_case.execute(input_dto)

        # 検証
        assert output.document_id == "123e4567-e89b-12d3-a456-426614174000"
        assert output.chunk_count == 3
        assert output.embeddings_generated == 3
        assert output.embeddings_skipped == 0
        assert output.embedding_model == "test-model"
        assert output.embedding_dimensions == 384
        assert output.status == "success"

        # リポジトリとサービスの呼び出しを確認
        mock_repository.find_by_id.assert_called_once()
        mock_embedding_service.generate_batch_embeddings.assert_called_once_with(
            ["Chunk content 0", "Chunk content 1", "Chunk content 2"]
        )
        mock_repository.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_document_not_found(
        self,
        use_case: GenerateEmbeddingsUseCase,
        mock_repository: Mock,
    ) -> None:
        """文書が見つからない場合にエラーが発生することを確認する。"""
        # セットアップ
        mock_repository.find_by_id = AsyncMock(return_value=None)

        # 実行と検証
        input_dto = GenerateEmbeddingsInput(
            document_id="550e8400-e29b-41d4-a716-446655440000"
        )
        with pytest.raises(ValueError, match="Document not found"):
            await use_case.execute(input_dto)

    @pytest.mark.asyncio
    async def test_execute_no_chunks(
        self,
        use_case: GenerateEmbeddingsUseCase,
        mock_repository: Mock,
        sample_document: Document,
    ) -> None:
        """チャンクがない文書の場合の処理を確認する。"""
        # セットアップ
        sample_document.chunks = []
        mock_repository.find_by_id = AsyncMock(return_value=sample_document)

        # 実行
        input_dto = GenerateEmbeddingsInput(
            document_id="123e4567-e89b-12d3-a456-426614174000"
        )
        output = await use_case.execute(input_dto)

        # 検証
        assert output.chunk_count == 0
        assert output.embeddings_generated == 0
        assert output.embeddings_skipped == 0
        assert output.status == "success"

    @pytest.mark.asyncio
    async def test_execute_skip_existing_embeddings(
        self,
        use_case: GenerateEmbeddingsUseCase,
        mock_repository: Mock,
        mock_embedding_service: Mock,
        sample_document: Document,
    ) -> None:
        """既存の埋め込みをスキップすることを確認する。"""
        # セットアップ（最初のチャンクに既に埋め込みがある）
        sample_document.chunks[0] = sample_document.chunks[0].with_embedding(
            [1.0] * 384
        )
        mock_repository.find_by_id = AsyncMock(return_value=sample_document)
        mock_repository.save = AsyncMock()

        embedding_results = [
            EmbeddingResult(
                embedding=[float(i)] * 384,
                model="test-model",
                dimensions=384,
            )
            for i in range(2)  # 2つのチャンクのみ処理
        ]
        mock_embedding_service.generate_batch_embeddings = AsyncMock(
            return_value=embedding_results
        )

        # 実行
        input_dto = GenerateEmbeddingsInput(
            document_id="123e4567-e89b-12d3-a456-426614174000", regenerate=False
        )
        output = await use_case.execute(input_dto)

        # 検証
        assert output.embeddings_generated == 2
        assert output.embeddings_skipped == 1
        assert output.status == "success"

        # 2つのチャンクのみ処理されることを確認
        mock_embedding_service.generate_batch_embeddings.assert_called_once_with(
            ["Chunk content 1", "Chunk content 2"]
        )

    @pytest.mark.asyncio
    async def test_execute_regenerate_all(
        self,
        use_case: GenerateEmbeddingsUseCase,
        mock_repository: Mock,
        mock_embedding_service: Mock,
        sample_document: Document,
    ) -> None:
        """regenerateフラグで全ての埋め込みを再生成することを確認する。"""
        # セットアップ（全てのチャンクに既に埋め込みがある）
        for i, chunk in enumerate(sample_document.chunks):
            sample_document.chunks[i] = chunk.with_embedding([0.5] * 384)

        mock_repository.find_by_id = AsyncMock(return_value=sample_document)
        mock_repository.save = AsyncMock()

        embedding_results = [
            EmbeddingResult(
                embedding=[float(i)] * 384,
                model="test-model",
                dimensions=384,
            )
            for i in range(3)
        ]
        mock_embedding_service.generate_batch_embeddings = AsyncMock(
            return_value=embedding_results
        )

        # 実行
        input_dto = GenerateEmbeddingsInput(
            document_id="123e4567-e89b-12d3-a456-426614174000", regenerate=True
        )
        output = await use_case.execute(input_dto)

        # 検証
        assert output.embeddings_generated == 3
        assert output.embeddings_skipped == 0
        assert output.status == "success"

    @pytest.mark.asyncio
    async def test_execute_embedding_generation_error(
        self,
        use_case: GenerateEmbeddingsUseCase,
        mock_repository: Mock,
        mock_embedding_service: Mock,
        sample_document: Document,
    ) -> None:
        """埋め込み生成でエラーが発生した場合の処理を確認する。"""
        # セットアップ
        mock_repository.find_by_id = AsyncMock(return_value=sample_document)
        mock_embedding_service.generate_batch_embeddings = AsyncMock(
            side_effect=Exception("API error")
        )

        # 実行
        input_dto = GenerateEmbeddingsInput(
            document_id="123e4567-e89b-12d3-a456-426614174000"
        )
        output = await use_case.execute(input_dto)

        # 検証
        assert output.status == "failed"
        assert output.embeddings_generated == 0
        assert output.chunk_count == 3

    @pytest.mark.asyncio
    async def test_execute_all_chunks_have_embeddings(
        self,
        use_case: GenerateEmbeddingsUseCase,
        mock_repository: Mock,
        sample_document: Document,
    ) -> None:
        """全てのチャンクが既に埋め込みを持っている場合の処理を確認する。"""
        # セットアップ
        for i, chunk in enumerate(sample_document.chunks):
            sample_document.chunks[i] = chunk.with_embedding([0.5] * 384)

        mock_repository.find_by_id = AsyncMock(return_value=sample_document)

        # 実行
        input_dto = GenerateEmbeddingsInput(
            document_id="123e4567-e89b-12d3-a456-426614174000", regenerate=False
        )
        output = await use_case.execute(input_dto)

        # 検証
        assert output.embeddings_generated == 0
        assert output.embeddings_skipped == 3
        assert output.status == "success"
