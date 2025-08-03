"""DocumentChunk値オブジェクトのテスト。"""

import uuid

import pytest
from pydantic import ValidationError

from src.domain.value_objects import ChunkMetadata, DocumentChunk, DocumentId


class TestDocumentChunk:
    """DocumentChunkのテストクラス。"""

    def setup_method(self) -> None:
        """テストメソッドのセットアップ。"""
        self.document_id = DocumentId.generate()
        self.chunk_metadata = ChunkMetadata(
            chunk_index=0,
            start_position=0,
            end_position=1000,
            total_chunks=3,
            overlap_with_previous=0,
            overlap_with_next=200,
        )

    def test_create_without_embedding(self) -> None:
        """埋め込みベクトルなしで作成できることを確認する。"""
        chunk = DocumentChunk(
            id=str(uuid.uuid4()),
            document_id=self.document_id,
            content="これはテスト用のチャンクテキストです。",
            metadata=self.chunk_metadata,
        )

        assert chunk.document_id == self.document_id
        assert chunk.content == "これはテスト用のチャンクテキストです。"
        assert chunk.embedding is None
        assert chunk.metadata == self.chunk_metadata
        assert not chunk.has_embedding

    def test_create_with_embedding(self) -> None:
        """埋め込みベクトルありで作成できることを確認する。"""
        embedding = [0.1] * 1536  # 1536次元のベクトル
        chunk = DocumentChunk(
            id=str(uuid.uuid4()),
            document_id=self.document_id,
            content="埋め込み付きチャンク",
            embedding=embedding,
            metadata=self.chunk_metadata,
        )

        assert chunk.embedding == embedding
        assert chunk.has_embedding

    def test_empty_content_validation(self) -> None:
        """空のコンテンツでエラーになることを確認する。"""
        with pytest.raises(ValidationError):
            DocumentChunk(
                id=str(uuid.uuid4()),
                document_id=self.document_id,
                content="",  # 空文字列は無効
                metadata=self.chunk_metadata,
            )

    def test_with_embedding(self) -> None:
        """埋め込みベクトルを追加できることを確認する。"""
        chunk = DocumentChunk(
            id=str(uuid.uuid4()),
            document_id=self.document_id,
            content="埋め込みを後から追加",
            metadata=self.chunk_metadata,
        )

        assert not chunk.has_embedding

        embedding = [0.2] * 1536
        chunk_with_embedding = chunk.with_embedding(embedding)

        # 元のインスタンスは変更されない
        assert not chunk.has_embedding
        assert chunk.embedding is None

        # 新しいインスタンスには埋め込みが設定されている
        assert chunk_with_embedding.has_embedding
        assert chunk_with_embedding.embedding == embedding
        assert chunk_with_embedding.content == chunk.content
        assert chunk_with_embedding.id == chunk.id

    def test_immutability(self) -> None:
        """不変性が保たれることを確認する。"""
        chunk = DocumentChunk(
            id=str(uuid.uuid4()),
            document_id=self.document_id,
            content="不変性テスト",
            metadata=self.chunk_metadata,
        )

        # frozen=Trueなので値の変更はできない
        with pytest.raises(ValidationError):
            chunk.content = "変更されたコンテンツ"

        with pytest.raises(ValidationError):
            chunk.embedding = [0.3] * 1536


class TestChunkMetadata:
    """ChunkMetadataのテストクラス。"""

    def test_create_basic_metadata(self) -> None:
        """基本的なメタデータを作成できることを確認する。"""
        metadata = ChunkMetadata(
            chunk_index=0,
            start_position=0,
            end_position=1000,
            total_chunks=5,
        )

        assert metadata.chunk_index == 0
        assert metadata.start_position == 0
        assert metadata.end_position == 1000
        assert metadata.total_chunks == 5
        assert metadata.overlap_with_previous == 0
        assert metadata.overlap_with_next == 0

    def test_create_with_overlap(self) -> None:
        """オーバーラップ付きのメタデータを作成できることを確認する。"""
        metadata = ChunkMetadata(
            chunk_index=1,
            start_position=800,
            end_position=1800,
            total_chunks=3,
            overlap_with_previous=200,
            overlap_with_next=200,
        )

        assert metadata.overlap_with_previous == 200
        assert metadata.overlap_with_next == 200

    def test_chunk_size_property(self) -> None:
        """チャンクサイズが正しく計算されることを確認する。"""
        metadata = ChunkMetadata(
            chunk_index=0,
            start_position=100,
            end_position=1100,
            total_chunks=1,
        )

        assert metadata.chunk_size == 1000

    def test_is_first_chunk_property(self) -> None:
        """最初のチャンク判定が正しく動作することを確認する。"""
        first_chunk = ChunkMetadata(
            chunk_index=0,
            start_position=0,
            end_position=1000,
            total_chunks=3,
        )
        assert first_chunk.is_first_chunk

        middle_chunk = ChunkMetadata(
            chunk_index=1,
            start_position=800,
            end_position=1800,
            total_chunks=3,
        )
        assert not middle_chunk.is_first_chunk

    def test_is_last_chunk_property(self) -> None:
        """最後のチャンク判定が正しく動作することを確認する。"""
        last_chunk = ChunkMetadata(
            chunk_index=2,
            start_position=1600,
            end_position=2400,
            total_chunks=3,
        )
        assert last_chunk.is_last_chunk

        middle_chunk = ChunkMetadata(
            chunk_index=1,
            start_position=800,
            end_position=1800,
            total_chunks=3,
        )
        assert not middle_chunk.is_last_chunk

    def test_invalid_values(self) -> None:
        """無効な値でエラーになることを確認する。"""
        # 負のインデックス
        with pytest.raises(ValidationError):
            ChunkMetadata(
                chunk_index=-1,
                start_position=0,
                end_position=1000,
                total_chunks=1,
            )

        # 負の開始位置
        with pytest.raises(ValidationError):
            ChunkMetadata(
                chunk_index=0,
                start_position=-1,
                end_position=1000,
                total_chunks=1,
            )

        # 終了位置が0以下
        with pytest.raises(ValidationError):
            ChunkMetadata(
                chunk_index=0,
                start_position=0,
                end_position=0,
                total_chunks=1,
            )

        # チャンク数が0
        with pytest.raises(ValidationError):
            ChunkMetadata(
                chunk_index=0,
                start_position=0,
                end_position=1000,
                total_chunks=0,
            )
