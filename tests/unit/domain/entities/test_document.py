"""Documentエンティティのテスト。"""

import uuid

import pytest

from src.domain.entities import Document
from src.domain.exceptions import DocumentValidationError
from src.domain.value_objects import (
    ChunkMetadata,
    DocumentChunk,
    DocumentId,
    DocumentMetadata,
)


class TestDocument:
    """Documentエンティティのテストクラス。"""

    def setup_method(self) -> None:
        """テストメソッドのセットアップ。"""
        self.metadata = DocumentMetadata.create_new(
            file_name="test.pdf",
            file_size=1024,
            content_type="application/pdf",
            category="テスト",
            tags=["サンプル"],
        )

    def test_create_new_document(self) -> None:
        """新しい文書を作成できることを確認する。"""
        title = "テスト文書"
        content = b"This is test content"

        document = Document.create(
            title=title,
            content=content,
            metadata=self.metadata,
        )

        assert document.title == title
        assert document.content == content
        assert document.metadata == self.metadata
        assert document.version == 1
        assert document.chunks == []
        assert document.id.value  # IDが生成されている

    def test_create_with_specific_id(self) -> None:
        """指定したIDで文書を作成できることを確認する。"""
        doc_id = DocumentId.generate()

        document = Document.create(
            title="指定ID文書",
            content=b"content",
            metadata=self.metadata,
            document_id=doc_id,
        )

        assert document.id == doc_id

    def test_title_validation(self) -> None:
        """タイトルのバリデーションが動作することを確認する。"""
        # 空白のみのタイトル
        with pytest.raises(DocumentValidationError) as exc_info:
            Document.create(
                title="   ",
                content=b"content",
                metadata=self.metadata,
            )
        assert exc_info.value.field == "title"

        # 256文字以上のタイトル
        long_title = "a" * 256
        with pytest.raises(DocumentValidationError) as exc_info:
            Document.create(
                title=long_title,
                content=b"content",
                metadata=self.metadata,
            )
        assert exc_info.value.field == "title"

    def test_add_chunk(self) -> None:
        """チャンクを追加できることを確認する。"""
        document = Document.create(
            title="チャンク追加テスト",
            content=b"content",
            metadata=self.metadata,
        )

        chunk_metadata = ChunkMetadata(
            chunk_index=0,
            start_position=0,
            end_position=100,
            total_chunks=1,
        )

        chunk = DocumentChunk(
            id=str(uuid.uuid4()),
            document_id=document.id,
            content="チャンクコンテンツ",
            metadata=chunk_metadata,
        )

        document.add_chunk(chunk)
        assert len(document.chunks) == 1
        assert document.chunks[0] == chunk
        assert document.chunk_count == 1
        assert document.has_chunks

    def test_add_chunk_from_different_document(self) -> None:
        """異なる文書のチャンクを追加しようとするとエラーになることを確認する。"""
        document1 = Document.create(
            title="文書1",
            content=b"content1",
            metadata=self.metadata,
        )

        document2 = Document.create(
            title="文書2",
            content=b"content2",
            metadata=self.metadata,
        )

        chunk_metadata = ChunkMetadata(
            chunk_index=0,
            start_position=0,
            end_position=100,
            total_chunks=1,
        )

        # document2用のチャンク
        chunk = DocumentChunk(
            id=str(uuid.uuid4()),
            document_id=document2.id,
            content="別文書のチャンク",
            metadata=chunk_metadata,
        )

        # document1に追加しようとするとエラー
        with pytest.raises(ValueError) as exc_info:
            document1.add_chunk(chunk)
        assert "different document" in str(exc_info.value)

    def test_update_metadata(self) -> None:
        """メタデータを更新できることを確認する。"""
        document = Document.create(
            title="メタデータ更新テスト",
            content=b"content",
            metadata=self.metadata,
        )

        original_version = document.version
        original_updated_at = document.metadata.updated_at

        new_metadata = DocumentMetadata.create_new(
            file_name="updated.pdf",
            file_size=2048,
            content_type="application/pdf",
            category="更新済み",
        )

        document.update_metadata(new_metadata)

        assert document.metadata.file_name == "updated.pdf"
        assert document.metadata.file_size == 2048
        assert document.metadata.category == "更新済み"
        assert document.metadata.updated_at > original_updated_at
        assert document.version == original_version + 1

    def test_clear_chunks(self) -> None:
        """チャンクをクリアできることを確認する。"""
        document = Document.create(
            title="チャンククリアテスト",
            content=b"content",
            metadata=self.metadata,
        )

        # チャンクを追加
        for i in range(3):
            chunk_metadata = ChunkMetadata(
                chunk_index=i,
                start_position=i * 100,
                end_position=(i + 1) * 100,
                total_chunks=3,
            )
            chunk = DocumentChunk(
                id=str(uuid.uuid4()),
                document_id=document.id,
                content=f"チャンク{i}",
                metadata=chunk_metadata,
            )
            document.add_chunk(chunk)

        assert document.chunk_count == 3

        document.clear_chunks()
        assert document.chunk_count == 0
        assert not document.has_chunks

    def test_get_chunk_by_index(self) -> None:
        """インデックスでチャンクを取得できることを確認する。"""
        document = Document.create(
            title="チャンク取得テスト",
            content=b"content",
            metadata=self.metadata,
        )

        # 3つのチャンクを追加
        chunks = []
        for i in range(3):
            chunk_metadata = ChunkMetadata(
                chunk_index=i,
                start_position=i * 100,
                end_position=(i + 1) * 100,
                total_chunks=3,
            )
            chunk = DocumentChunk(
                id=str(uuid.uuid4()),
                document_id=document.id,
                content=f"チャンク{i}",
                metadata=chunk_metadata,
            )
            chunks.append(chunk)
            document.add_chunk(chunk)

        # インデックスで取得
        assert document.get_chunk_by_index(0) == chunks[0]
        assert document.get_chunk_by_index(1) == chunks[1]
        assert document.get_chunk_by_index(2) == chunks[2]
        assert document.get_chunk_by_index(3) is None  # 存在しないインデックス

    def test_all_chunks_have_embeddings(self) -> None:
        """すべてのチャンクに埋め込みがあるかを判定できることを確認する。"""
        document = Document.create(
            title="埋め込みチェックテスト",
            content=b"content",
            metadata=self.metadata,
        )

        # 埋め込みなしのチャンクを追加
        chunk_metadata = ChunkMetadata(
            chunk_index=0,
            start_position=0,
            end_position=100,
            total_chunks=2,
        )
        chunk_without_embedding = DocumentChunk(
            id=str(uuid.uuid4()),
            document_id=document.id,
            content="埋め込みなし",
            metadata=chunk_metadata,
        )
        document.add_chunk(chunk_without_embedding)

        assert not document.all_chunks_have_embeddings

        # 埋め込みありのチャンクを追加
        chunk_metadata2 = ChunkMetadata(
            chunk_index=1,
            start_position=100,
            end_position=200,
            total_chunks=2,
        )
        chunk_with_embedding = DocumentChunk(
            id=str(uuid.uuid4()),
            document_id=document.id,
            content="埋め込みあり",
            embedding=[0.1] * 1536,
            metadata=chunk_metadata2,
        )
        document.add_chunk(chunk_with_embedding)

        # まだすべてのチャンクに埋め込みがあるわけではない
        assert not document.all_chunks_have_embeddings

        # 最初のチャンクに埋め込みを追加
        document.chunks[0] = chunk_without_embedding.with_embedding([0.2] * 1536)

        # 今度はすべてのチャンクに埋め込みがある
        assert document.all_chunks_have_embeddings
