"""SQLAlchemyモデル定義。"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from src.domain.entities import Document as DomainDocument
from src.domain.value_objects import (
    ChunkMetadata,
    DocumentId,
    DocumentMetadata,
)
from src.domain.value_objects import (
    DocumentChunk as DomainDocumentChunk,
)

from .connection import Base


class DocumentModel(Base):
    """文書テーブルのSQLAlchemyモデル。"""

    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=True)
    content = Column(Text, nullable=False)  # バイナリデータはBase64エンコードして保存
    document_metadata = Column(JSON, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # リレーション
    chunks = relationship(
        "DocumentChunkModel", back_populates="document", cascade="all, delete-orphan"
    )

    def to_domain(self) -> DomainDocument:
        """ドメインエンティティに変換する。

        Returns:
            DomainDocument: ドメインの文書エンティティ
        """
        # メタデータの復元
        metadata_dict: dict[str, Any] = self.document_metadata or {}  # type: ignore[assignment]
        document_metadata = DocumentMetadata(
            file_name=metadata_dict.get("file_name", ""),
            file_size=metadata_dict.get("file_size", 0),
            content_type=metadata_dict.get("content_type", ""),
            category=metadata_dict.get("category"),
            tags=metadata_dict.get("tags", []),
            created_at=self.created_at,  # type: ignore[arg-type]
            updated_at=self.updated_at,  # type: ignore[arg-type]
            author=metadata_dict.get("author"),
            description=metadata_dict.get("description"),
        )

        # ドメインエンティティの作成
        domain_document = DomainDocument(
            id=DocumentId(value=str(self.id)),
            title=self.title,  # type: ignore[arg-type]
            content=self.content.encode("utf-8") if self.content else b"",
            metadata=document_metadata,
            chunks=[],
            version=self.version,  # type: ignore[arg-type]
        )

        # チャンクの追加
        for chunk_model in self.chunks:
            domain_document.chunks.append(chunk_model.to_domain())

        return domain_document

    @classmethod
    def from_domain(cls, document: DomainDocument) -> "DocumentModel":
        """ドメインエンティティからモデルを作成する。

        Args:
            document: ドメインの文書エンティティ

        Returns:
            DocumentModel: SQLAlchemyモデル
        """
        # メタデータの変換
        metadata_dict = {
            "file_name": document.metadata.file_name,
            "file_size": document.metadata.file_size,
            "content_type": document.metadata.content_type,
            "category": document.metadata.category,
            "tags": document.metadata.tags,
            "author": document.metadata.author,
            "description": document.metadata.description,
        }

        model = cls(
            id=uuid.UUID(document.id.value),
            title=document.title,
            content=document.content.decode("utf-8") if document.content else "",
            document_metadata=metadata_dict,
            version=document.version,
            created_at=document.metadata.created_at,
            updated_at=document.metadata.updated_at,
        )

        # ファイルパスの設定（存在する場合）
        if hasattr(document, "file_path"):
            model.file_path = document.file_path

        return model


class DocumentChunkModel(Base):
    """文書チャンクテーブルのSQLAlchemyモデル。"""

    __tablename__ = "document_chunks"

    id = Column(String(36), primary_key=True)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(JSON, nullable=True)  # ベクトルはJSONとして保存
    chunk_metadata = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # リレーション
    document = relationship("DocumentModel", back_populates="chunks")

    def to_domain(self) -> DomainDocumentChunk:
        """ドメイン値オブジェクトに変換する。

        Returns:
            DomainDocumentChunk: ドメインの文書チャンク値オブジェクト
        """
        # メタデータの復元
        metadata_dict: dict[str, Any] = self.chunk_metadata or {}  # type: ignore[assignment]
        chunk_metadata = ChunkMetadata(
            chunk_index=metadata_dict.get("chunk_index", 0),
            start_position=metadata_dict.get("start_position", 0),
            end_position=metadata_dict.get("end_position", 0),
            total_chunks=metadata_dict.get("total_chunks", 1),
            overlap_with_previous=metadata_dict.get("overlap_with_previous", 0),
            overlap_with_next=metadata_dict.get("overlap_with_next", 0),
        )

        return DomainDocumentChunk(
            id=self.id,  # type: ignore[arg-type]
            document_id=DocumentId(value=str(self.document_id)),
            content=self.content,  # type: ignore[arg-type]
            embedding=self.embedding if self.embedding else None,  # type: ignore[arg-type]
            metadata=chunk_metadata,
        )

    @classmethod
    def from_domain(cls, chunk: DomainDocumentChunk) -> "DocumentChunkModel":
        """ドメイン値オブジェクトからモデルを作成する。

        Args:
            chunk: ドメインの文書チャンク値オブジェクト

        Returns:
            DocumentChunkModel: SQLAlchemyモデル
        """
        # メタデータの変換
        metadata_dict = {
            "chunk_index": chunk.metadata.chunk_index,
            "start_position": chunk.metadata.start_position,
            "end_position": chunk.metadata.end_position,
            "total_chunks": chunk.metadata.total_chunks,
            "overlap_with_previous": chunk.metadata.overlap_with_previous,
            "overlap_with_next": chunk.metadata.overlap_with_next,
        }

        return cls(
            id=chunk.id,
            document_id=uuid.UUID(chunk.document_id.value),
            content=chunk.content,
            embedding=chunk.embedding,
            chunk_metadata=metadata_dict,
        )
