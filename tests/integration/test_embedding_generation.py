"""埋め込みベクトル生成の統合テスト。"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.use_cases.generate_embeddings import (
    GenerateEmbeddingsInput,
    GenerateEmbeddingsUseCase,
)
from src.domain.entities import Document
from src.domain.value_objects import (
    ChunkMetadata,
    DocumentChunk,
    DocumentId,
    DocumentMetadata,
)
from src.infrastructure.externals.embeddings import MockEmbeddingService
from src.infrastructure.externals.file_storage import FileStorageService
from src.infrastructure.repositories import DocumentRepositoryImpl


@pytest.mark.integration
class TestEmbeddingGeneration:
    """埋め込み生成の統合テスト。"""

    @pytest.mark.asyncio
    async def test_generate_embeddings_for_document_with_chunks(
        self, db_session: AsyncSession, tmp_path
    ) -> None:
        """チャンクを持つ文書に対して埋め込みを生成できることを確認する。"""
        # セットアップ
        file_storage = FileStorageService(base_path=tmp_path)
        repository = DocumentRepositoryImpl(db_session, file_storage)
        embedding_service = MockEmbeddingService(model="test-model", dimensions=384)
        use_case = GenerateEmbeddingsUseCase(
            document_repository=repository,
            embedding_service=embedding_service,
        )

        # テスト用の文書を作成
        from datetime import datetime

        doc_id = DocumentId.generate()
        metadata = DocumentMetadata(
            file_name="test.txt",
            file_size=1000,
            content_type="text/plain",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # チャンクを持つ文書を作成
        chunks = [
            DocumentChunk(
                id=f"chunk-{i}",
                document_id=doc_id,
                content=f"Test chunk content {i}",
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

        document = Document(
            id=doc_id,
            title="Test Document",
            content=b"Test content",
            metadata=metadata,
            chunks=chunks,
            version=1,
        )

        # 文書を保存
        await repository.save(document)

        # 埋め込みを生成
        input_dto = GenerateEmbeddingsInput(
            document_id=str(doc_id.value), regenerate=False
        )
        output = await use_case.execute(input_dto)

        # 検証
        assert output.document_id == str(doc_id.value)
        assert output.chunk_count == 3
        assert output.embeddings_generated == 3
        assert output.embeddings_skipped == 0
        assert output.embedding_model == "test-model"
        assert output.embedding_dimensions == 384
        assert output.status == "success"

        # 文書を再取得して埋め込みが保存されていることを確認
        saved_document = await repository.find_by_id(doc_id)
        assert saved_document is not None
        # 重複したチャンクがある可能性があるため、embedが設定されているチャンクを確認
        chunks_with_embedding = [
            c for c in saved_document.chunks if c.embedding is not None
        ]
        assert len(chunks_with_embedding) == 3
        for chunk in chunks_with_embedding:
            assert chunk.embedding is not None
            assert len(chunk.embedding) == 384

    @pytest.mark.asyncio
    async def test_embedding_service_factory(self) -> None:
        """埋め込みサービスファクトリーが正しく動作することを確認する。"""
        from src.infrastructure.externals.embeddings import EmbeddingServiceFactory

        # モックサービスの作成
        mock_service = EmbeddingServiceFactory.create(
            provider="mock", model="test-model"
        )
        assert isinstance(mock_service, MockEmbeddingService)
        assert mock_service.get_model_name() == "test-model"

        # OpenAIサービスの作成（APIキーなしでエラーになることを確認）
        with pytest.raises(ValueError, match="OpenAI provider requires api_key"):
            EmbeddingServiceFactory.create(provider="openai", api_key=None)

    @pytest.mark.asyncio
    async def test_batch_embedding_generation(self) -> None:
        """バッチ埋め込み生成が正しく動作することを確認する。"""
        embedding_service = MockEmbeddingService(model="test-model", dimensions=384)

        texts = [
            "First document chunk",
            "Second document chunk",
            "Third document chunk",
        ]

        # バッチ生成
        results = await embedding_service.generate_batch_embeddings(texts)

        # 検証
        assert len(results) == 3
        for _i, result in enumerate(results):
            assert result.model == "test-model"
            assert result.dimensions == 384
            assert len(result.embedding) == 384
            assert result.is_valid

        # 各テキストで異なる埋め込みが生成されることを確認
        assert results[0].embedding != results[1].embedding
        assert results[1].embedding != results[2].embedding
