"""文書エンティティ。"""

from pydantic import BaseModel, Field, field_validator

from ..exceptions import DocumentValidationError
from ..value_objects import DocumentChunk, DocumentId, DocumentMetadata


class Document(BaseModel):
    """文書を表すエンティティ。

    Attributes:
        id: 文書の一意識別子
        title: 文書のタイトル
        content: 文書の内容（バイト列）
        metadata: 文書のメタデータ
        chunks: 文書のチャンクリスト
        version: 文書のバージョン
    """

    id: DocumentId = Field(..., description="文書の一意識別子")
    title: str = Field(..., min_length=1, description="文書のタイトル")
    content: bytes = Field(..., description="文書の内容（バイト列）")
    metadata: DocumentMetadata = Field(..., description="文書のメタデータ")
    chunks: list[DocumentChunk] = Field(
        default_factory=list, description="文書のチャンクリスト"
    )
    version: int = Field(default=1, ge=1, description="文書のバージョン")

    model_config = {"validate_assignment": True}

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """タイトルのバリデーション。"""
        if len(v.strip()) == 0:
            raise DocumentValidationError("title", "Title cannot be empty")
        if len(v) > 255:
            raise DocumentValidationError("title", "Title cannot exceed 255 characters")
        return v.strip()

    @classmethod
    def create(
        cls,
        title: str,
        content: bytes,
        metadata: DocumentMetadata,
        document_id: DocumentId | None = None,
    ) -> "Document":
        """新しい文書を作成する。

        Args:
            title: 文書のタイトル
            content: 文書の内容
            metadata: 文書のメタデータ
            document_id: 文書ID（指定しない場合は自動生成）

        Returns:
            新しいDocumentインスタンス
        """
        return cls(
            id=document_id or DocumentId.generate(),
            title=title,
            content=content,
            metadata=metadata,
            chunks=[],
            version=1,
        )

    def add_chunk(self, chunk: DocumentChunk) -> None:
        """チャンクを追加する。

        Args:
            chunk: 追加するチャンク

        Raises:
            ValueError: チャンクが異なる文書のものである場合
        """
        if chunk.document_id != self.id:
            raise ValueError(
                f"Chunk belongs to different document: {chunk.document_id}"
            )
        self.chunks.append(chunk)

    def update_metadata(self, metadata: DocumentMetadata) -> None:
        """メタデータを更新する。

        Args:
            metadata: 新しいメタデータ
        """
        self.metadata = metadata.update_timestamp()
        self.increment_version()

    def increment_version(self) -> None:
        """バージョンを1増やす。"""
        self.version += 1

    def clear_chunks(self) -> None:
        """すべてのチャンクをクリアする。"""
        self.chunks.clear()

    @property
    def chunk_count(self) -> int:
        """チャンク数を返す。"""
        return len(self.chunks)

    @property
    def has_chunks(self) -> bool:
        """チャンクが存在するかを判定する。"""
        return len(self.chunks) > 0

    @property
    def all_chunks_have_embeddings(self) -> bool:
        """すべてのチャンクに埋め込みベクトルが設定されているかを判定する。"""
        return all(chunk.has_embedding for chunk in self.chunks)

    def get_chunk_by_index(self, index: int) -> DocumentChunk | None:
        """インデックスでチャンクを取得する。

        Args:
            index: チャンクのインデックス

        Returns:
            該当するチャンク、存在しない場合はNone
        """
        for chunk in self.chunks:
            if chunk.metadata.chunk_index == index:
                return chunk
        return None
