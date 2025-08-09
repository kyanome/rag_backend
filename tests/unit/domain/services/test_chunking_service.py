"""ChunkingServiceのテスト。"""

import pytest

from src.domain.entities import Document
from src.domain.externals import ChunkingStrategy
from src.domain.services import ChunkingService
from src.domain.value_objects import DocumentMetadata


class MockChunkingStrategy(ChunkingStrategy):
    """モックのチャンク分割戦略。"""

    def split_text(
        self, text: str, chunk_size: int, overlap_size: int
    ) -> list[tuple[str, int, int]]:
        """テキストを固定サイズで分割する。"""
        chunks = []
        step = chunk_size - overlap_size
        for i in range(0, len(text), step):
            end = min(i + chunk_size, len(text))
            chunks.append((text[i:end], i, end))
            if end >= len(text):
                break
        return chunks

    def estimate_chunk_count(
        self, text: str, chunk_size: int, overlap_size: int
    ) -> int:
        """チャンク数を推定する。"""
        if not text:
            return 0
        if len(text) <= chunk_size:
            return 1
        step = chunk_size - overlap_size
        return (len(text) + step - 1) // step


class TestChunkingService:
    """ChunkingServiceのテスト。"""

    @pytest.fixture
    def service(self) -> ChunkingService:
        """ChunkingServiceインスタンスを作成する。"""
        return ChunkingService()

    @pytest.fixture
    def strategy(self) -> MockChunkingStrategy:
        """モック戦略を作成する。"""
        return MockChunkingStrategy()

    @pytest.fixture
    def document(self) -> Document:
        """テスト用文書を作成する。"""
        metadata = DocumentMetadata.create_new(
            file_name="test.txt",
            file_size=1000,
            content_type="text/plain",
        )
        return Document.create(
            title="Test Document",
            content=b"Test content",
            metadata=metadata,
        )

    def test_create_chunks_empty_text(
        self,
        service: ChunkingService,
        document: Document,
        strategy: MockChunkingStrategy,
    ) -> None:
        """空のテキストでチャンクが作成されないことを確認する。"""
        chunks = service.create_chunks(
            document=document,
            text="",
            strategy=strategy,
            chunk_size=100,
            overlap_size=20,
        )
        assert len(chunks) == 0

    def test_create_chunks_single_chunk(
        self,
        service: ChunkingService,
        document: Document,
        strategy: MockChunkingStrategy,
    ) -> None:
        """短いテキストで単一のチャンクが作成されることを確認する。"""
        text = "This is a short text."
        chunks = service.create_chunks(
            document=document,
            text=text,
            strategy=strategy,
            chunk_size=100,
            overlap_size=20,
        )

        assert len(chunks) == 1
        assert chunks[0].content == text
        assert chunks[0].document_id == document.id
        assert chunks[0].metadata.chunk_index == 0
        assert chunks[0].metadata.total_chunks == 1

    def test_create_chunks_multiple_chunks(
        self,
        service: ChunkingService,
        document: Document,
        strategy: MockChunkingStrategy,
    ) -> None:
        """長いテキストで複数のチャンクが作成されることを確認する。"""
        text = "a" * 250  # 250文字のテキスト
        chunks = service.create_chunks(
            document=document,
            text=text,
            strategy=strategy,
            chunk_size=100,
            overlap_size=20,
        )

        # (100-20) = 80文字ずつ進むので、4つのチャンクが必要
        # 0-100, 80-180, 160-250 (実際のstrategyの動作による)
        assert len(chunks) >= 3  # 少なくとも3つ以上のチャンク
        assert all(chunk.document_id == document.id for chunk in chunks)
        assert chunks[0].metadata.chunk_index == 0
        assert chunks[-1].metadata.chunk_index == len(chunks) - 1

    def test_create_chunks_with_overlap(
        self,
        service: ChunkingService,
        document: Document,
        strategy: MockChunkingStrategy,
    ) -> None:
        """オーバーラップが正しく計算されることを確認する。"""
        text = "0123456789" * 10  # 100文字
        chunks = service.create_chunks(
            document=document,
            text=text,
            strategy=strategy,
            chunk_size=30,
            overlap_size=10,
        )

        # チャンク間のオーバーラップを確認
        for i in range(len(chunks) - 1):
            current_end = chunks[i].metadata.end_position
            next_start = chunks[i + 1].metadata.start_position
            if next_start < current_end:
                assert chunks[i].metadata.overlap_with_next > 0

    def test_update_document_chunks(
        self,
        service: ChunkingService,
        document: Document,
        strategy: MockChunkingStrategy,
    ) -> None:
        """文書のチャンクが更新されることを確認する。"""
        text = "Test text for chunking"
        chunks = service.create_chunks(
            document=document,
            text=text,
            strategy=strategy,
            chunk_size=10,
            overlap_size=2,
        )

        # チャンクを文書に追加
        service.update_document_chunks(document, chunks)

        assert document.chunk_count == len(chunks)
        assert document.has_chunks
        assert all(chunk in document.chunks for chunk in chunks)

    def test_validate_parameters_invalid_chunk_size(
        self, service: ChunkingService
    ) -> None:
        """無効なチャンクサイズでエラーが発生することを確認する。"""
        with pytest.raises(ValueError, match="Chunk size must be positive"):
            service._validate_parameters(chunk_size=0, overlap_size=10)

        with pytest.raises(ValueError, match="Chunk size must be positive"):
            service._validate_parameters(chunk_size=-1, overlap_size=10)

    def test_validate_parameters_invalid_overlap_size(
        self, service: ChunkingService
    ) -> None:
        """無効なオーバーラップサイズでエラーが発生することを確認する。"""
        with pytest.raises(ValueError, match="Overlap size must be non-negative"):
            service._validate_parameters(chunk_size=100, overlap_size=-1)

        with pytest.raises(
            ValueError, match="Overlap size must be less than chunk size"
        ):
            service._validate_parameters(chunk_size=100, overlap_size=100)

        with pytest.raises(
            ValueError, match="Overlap size must be less than chunk size"
        ):
            service._validate_parameters(chunk_size=100, overlap_size=150)

    def test_calculate_chunking_metrics(self, service: ChunkingService) -> None:
        """チャンク化メトリクスが正しく計算されることを確認する。"""
        text = "a" * 250
        metrics = service.calculate_chunking_metrics(
            text=text,
            chunk_size=100,
            overlap_size=20,
        )

        assert metrics["text_length"] == 250
        assert metrics["chunk_size"] == 100
        assert metrics["overlap_size"] == 20
        assert metrics["estimated_chunks"] > 0

    def test_calculate_chunking_metrics_empty_text(
        self, service: ChunkingService
    ) -> None:
        """空のテキストでメトリクスが正しく計算されることを確認する。"""
        metrics = service.calculate_chunking_metrics(
            text="",
            chunk_size=100,
            overlap_size=20,
        )

        assert metrics["text_length"] == 0
        assert metrics["estimated_chunks"] == 0
