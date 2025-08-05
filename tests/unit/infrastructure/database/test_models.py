"""SQLAlchemyモデルのテスト。"""

import base64
import uuid
from datetime import UTC, datetime

from src.domain.entities import Document
from src.domain.value_objects import (
    ChunkMetadata,
    DocumentChunk,
    DocumentId,
    DocumentMetadata,
)
from src.infrastructure.database.models import DocumentChunkModel, DocumentModel


class TestDocumentModel:
    """DocumentModelのテストクラス。"""

    def test_from_domain(self) -> None:
        """ドメインエンティティからモデルへの変換をテストする。"""
        # ドメインエンティティの作成
        metadata = DocumentMetadata.create_new(
            file_name="test.pdf",
            file_size=1024,
            content_type="application/pdf",
            category="テスト",
            tags=["サンプル", "テスト"],
            author="テスト太郎",
            description="テスト用文書",
        )

        document = Document.create(
            title="テスト文書",
            content=b"Test content",
            metadata=metadata,
        )

        # モデルへの変換
        model = DocumentModel.from_domain(document)

        # 検証
        assert str(model.id) == document.id.value
        assert model.title == document.title
        assert model.content == base64.b64encode(document.content).decode("ascii")
        assert model.version == document.version
        assert model.document_metadata["file_name"] == metadata.file_name
        assert model.document_metadata["file_size"] == metadata.file_size
        assert model.document_metadata["content_type"] == metadata.content_type
        assert model.document_metadata["category"] == metadata.category
        assert model.document_metadata["tags"] == metadata.tags
        assert model.document_metadata["author"] == metadata.author
        assert model.document_metadata["description"] == metadata.description
        assert model.created_at == metadata.created_at
        assert model.updated_at == metadata.updated_at

    def test_to_domain(self) -> None:
        """モデルからドメインエンティティへの変換をテストする。"""
        # モデルの作成
        model_id = uuid.uuid4()
        created_at = datetime.now(UTC)
        updated_at = datetime.now(UTC)

        model = DocumentModel(
            id=model_id,
            title="テスト文書",
            content=base64.b64encode(b"Test content").decode("ascii"),
            file_path="test/path/test.pdf",
            document_metadata={
                "file_name": "test.pdf",
                "file_size": 1024,
                "content_type": "application/pdf",
                "category": "テスト",
                "tags": ["サンプル"],
                "author": "テスト太郎",
                "description": "テスト用文書",
            },
            version=2,
            created_at=created_at,
            updated_at=updated_at,
        )

        # ドメインエンティティへの変換
        document = model.to_domain()

        # 検証
        assert document.id.value == str(model_id)
        assert document.title == model.title
        assert document.content == b"Test content"
        assert document.version == model.version
        assert document.metadata.file_name == "test.pdf"
        assert document.metadata.file_size == 1024
        assert document.metadata.content_type == "application/pdf"
        assert document.metadata.category == "テスト"
        assert document.metadata.tags == ["サンプル"]
        assert document.metadata.author == "テスト太郎"
        assert document.metadata.description == "テスト用文書"
        assert document.metadata.created_at == created_at
        assert document.metadata.updated_at == updated_at

    def test_round_trip_conversion(self) -> None:
        """ドメイン→モデル→ドメインの往復変換をテストする。"""
        # 元のドメインエンティティ
        original = Document.create(
            title="往復テスト",
            content=b"Round trip test",
            metadata=DocumentMetadata.create_new(
                file_name="round_trip.txt",
                file_size=15,
                content_type="text/plain",
            ),
        )

        # 往復変換
        model = DocumentModel.from_domain(original)
        restored = model.to_domain()

        # 検証
        assert restored.id.value == original.id.value
        assert restored.title == original.title
        assert restored.content == original.content
        assert restored.version == original.version
        assert restored.metadata.file_name == original.metadata.file_name
        assert restored.metadata.file_size == original.metadata.file_size
        assert restored.metadata.content_type == original.metadata.content_type


class TestDocumentChunkModel:
    """DocumentChunkModelのテストクラス。"""

    def test_from_domain(self) -> None:
        """ドメイン値オブジェクトからモデルへの変換をテストする。"""
        # ドメイン値オブジェクトの作成
        document_id = DocumentId.generate()
        chunk_metadata = ChunkMetadata(
            chunk_index=0,
            start_position=0,
            end_position=100,
            total_chunks=3,
            overlap_with_previous=0,
            overlap_with_next=20,
        )

        chunk = DocumentChunk(
            id=str(uuid.uuid4()),
            document_id=document_id,
            content="チャンクコンテンツ",
            embedding=[0.1, 0.2, 0.3],
            metadata=chunk_metadata,
        )

        # モデルへの変換
        model = DocumentChunkModel.from_domain(chunk)

        # 検証
        assert model.id == chunk.id
        assert str(model.document_id) == document_id.value
        assert model.content == chunk.content
        assert model.embedding == chunk.embedding
        assert model.chunk_metadata["chunk_index"] == chunk_metadata.chunk_index
        assert model.chunk_metadata["start_position"] == chunk_metadata.start_position
        assert model.chunk_metadata["end_position"] == chunk_metadata.end_position
        assert model.chunk_metadata["total_chunks"] == chunk_metadata.total_chunks
        assert (
            model.chunk_metadata["overlap_with_previous"]
            == chunk_metadata.overlap_with_previous
        )
        assert (
            model.chunk_metadata["overlap_with_next"]
            == chunk_metadata.overlap_with_next
        )

    def test_to_domain(self) -> None:
        """モデルからドメイン値オブジェクトへの変換をテストする。"""
        # モデルの作成
        chunk_id = str(uuid.uuid4())
        document_id = uuid.uuid4()

        model = DocumentChunkModel(
            id=chunk_id,
            document_id=document_id,
            content="チャンクコンテンツ",
            embedding=[0.1, 0.2, 0.3],
            chunk_metadata={
                "chunk_index": 1,
                "start_position": 100,
                "end_position": 200,
                "total_chunks": 3,
                "overlap_with_previous": 20,
                "overlap_with_next": 20,
            },
        )

        # ドメイン値オブジェクトへの変換
        chunk = model.to_domain()

        # 検証
        assert chunk.id == chunk_id
        assert chunk.document_id.value == str(document_id)
        assert chunk.content == model.content
        assert chunk.embedding == model.embedding
        assert chunk.metadata.chunk_index == 1
        assert chunk.metadata.start_position == 100
        assert chunk.metadata.end_position == 200
        assert chunk.metadata.total_chunks == 3
        assert chunk.metadata.overlap_with_previous == 20
        assert chunk.metadata.overlap_with_next == 20

    def test_to_domain_without_embedding(self) -> None:
        """埋め込みベクトルなしでの変換をテストする。"""
        model = DocumentChunkModel(
            id=str(uuid.uuid4()),
            document_id=uuid.uuid4(),
            content="チャンクコンテンツ",
            embedding=None,
            chunk_metadata={
                "chunk_index": 0,
                "start_position": 0,
                "end_position": 100,
                "total_chunks": 1,
                "overlap_with_previous": 0,
                "overlap_with_next": 0,
            },
        )

        chunk = model.to_domain()

        assert chunk.embedding is None
        assert not chunk.has_embedding
