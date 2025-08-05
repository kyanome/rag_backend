"""SQLAlchemyモデル定義。"""

import base64
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PostgresUUID
from sqlalchemy.orm import relationship
from sqlalchemy.types import CHAR, TypeDecorator

from src.domain.entities import Document as DomainDocument
from src.domain.entities import Session as DomainSession
from src.domain.entities import User as DomainUser
from src.domain.value_objects import (
    ChunkMetadata,
    DocumentId,
    DocumentMetadata,
    Email,
    HashedPassword,
    UserId,
    UserRole,
)
from src.domain.value_objects import (
    DocumentChunk as DomainDocumentChunk,
)

from .connection import Base


class UUID(TypeDecorator):
    """プラットフォーム非依存のUUID型。

    PostgreSQLではUUID型を使用し、その他のDBでは
    CHAR(36)にUUID文字列を格納する。
    """

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PostgresUUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return value
        elif dialect.name == "postgresql":
            return value
        else:
            return str(value)

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return value
        elif dialect.name == "postgresql":
            return value
        else:
            return uuid.UUID(value)


class DocumentModel(Base):
    """文書テーブルのSQLAlchemyモデル。"""

    __tablename__ = "documents"

    id: Column[uuid.UUID] = Column(UUID(), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=True)
    content = Column(Text, nullable=False)  # バイナリデータはBase64エンコードして保存
    document_metadata = Column(JSON, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(),
        onupdate=lambda: datetime.now(),
        nullable=False,
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
            content=base64.b64decode(self.content) if self.content else b"",
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
            content=(
                base64.b64encode(document.content).decode("ascii")
                if document.content
                else ""
            ),
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
    document_id: Column[uuid.UUID] = Column(
        UUID(), ForeignKey("documents.id"), nullable=False
    )
    content = Column(Text, nullable=False)
    embedding = Column(JSON, nullable=True)  # ベクトルはJSONとして保存
    chunk_metadata = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(), nullable=False)

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


class UserModel(Base):
    """ユーザーテーブルのSQLAlchemyモデル。"""

    __tablename__ = "users"

    id: Column[uuid.UUID] = Column(UUID(), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_email_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(),
        onupdate=lambda: datetime.now(),
        nullable=False,
    )
    last_login_at = Column(DateTime, nullable=True)

    # リレーション
    sessions = relationship(
        "SessionModel", back_populates="user", cascade="all, delete-orphan"
    )

    def to_domain(self) -> DomainUser:
        """ドメインエンティティに変換する。

        Returns:
            DomainUser: ドメインのユーザーエンティティ
        """
        return DomainUser(
            id=UserId(value=str(self.id)),
            email=Email(value=self.email),  # type: ignore[arg-type]
            hashed_password=HashedPassword(value=self.hashed_password),  # type: ignore[arg-type]
            role=UserRole.from_name(self.role),  # type: ignore[arg-type]
            is_active=self.is_active,  # type: ignore[arg-type]
            is_email_verified=self.is_email_verified,  # type: ignore[arg-type]
            created_at=self.created_at,  # type: ignore[arg-type]
            updated_at=self.updated_at,  # type: ignore[arg-type]
            last_login_at=self.last_login_at,  # type: ignore[arg-type]
        )

    @classmethod
    def from_domain(cls, user: DomainUser) -> "UserModel":
        """ドメインエンティティからモデルを作成する。

        Args:
            user: ドメインのユーザーエンティティ

        Returns:
            UserModel: SQLAlchemyモデル
        """
        return cls(
            id=uuid.UUID(user.id.value),
            email=user.email.value,
            hashed_password=user.hashed_password.value,
            role=str(user.role),  # UserRole.__str__() returns the role name
            is_active=user.is_active,
            is_email_verified=user.is_email_verified,
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_login_at=user.last_login_at,
        )


class SessionModel(Base):
    """セッションテーブルのSQLAlchemyモデル。"""

    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True)
    user_id: Column[uuid.UUID] = Column(
        UUID(), ForeignKey("users.id"), nullable=False, index=True
    )
    access_token = Column(String(500), unique=True, nullable=False, index=True)
    refresh_token = Column(String(500), unique=True, nullable=False, index=True)
    access_token_expires_at = Column(DateTime, nullable=False)
    refresh_token_expires_at = Column(DateTime, nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(), nullable=False)
    last_accessed_at = Column(DateTime, default=lambda: datetime.now(), nullable=False)
    ip_address = Column(String(45), nullable=True)  # IPv6対応のため45文字
    user_agent = Column(String(500), nullable=True)

    # リレーション
    user = relationship("UserModel", back_populates="sessions")

    def to_domain(self) -> DomainSession:
        """ドメインエンティティに変換する。

        Returns:
            DomainSession: ドメインのセッションエンティティ
        """
        return DomainSession(
            id=self.id,  # type: ignore[arg-type]
            user_id=UserId(value=str(self.user_id)),
            access_token=self.access_token,  # type: ignore[arg-type]
            refresh_token=self.refresh_token,  # type: ignore[arg-type]
            access_token_expires_at=self.access_token_expires_at,  # type: ignore[arg-type]
            refresh_token_expires_at=self.refresh_token_expires_at,  # type: ignore[arg-type]
            created_at=self.created_at,  # type: ignore[arg-type]
            last_accessed_at=self.last_accessed_at,  # type: ignore[arg-type]
            ip_address=self.ip_address,  # type: ignore[arg-type]
            user_agent=self.user_agent,  # type: ignore[arg-type]
        )

    @classmethod
    def from_domain(cls, session: DomainSession) -> "SessionModel":
        """ドメインエンティティからモデルを作成する。

        Args:
            session: ドメインのセッションエンティティ

        Returns:
            SessionModel: SQLAlchemyモデル
        """
        return cls(
            id=session.id,
            user_id=uuid.UUID(session.user_id.value),
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            access_token_expires_at=session.access_token_expires_at,
            refresh_token_expires_at=session.refresh_token_expires_at,
            created_at=session.created_at,
            last_accessed_at=session.last_accessed_at,
            ip_address=session.ip_address,
            user_agent=session.user_agent,
        )
