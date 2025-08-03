"""文書チャンク値オブジェクト。"""

import uuid

from pydantic import BaseModel, Field

from .chunk_metadata import ChunkMetadata
from .document_id import DocumentId


class DocumentChunk(BaseModel):
    """文書の分割単位を表す値オブジェクト。

    Attributes:
        id: チャンクの一意識別子
        document_id: 所属する文書のID
        content: チャンクのテキスト内容
        embedding: 埋め込みベクトル（オプション）
        metadata: チャンクのメタデータ
    """

    id: str = Field(..., description="チャンクの一意識別子")
    document_id: DocumentId = Field(..., description="所属する文書のID")
    content: str = Field(..., min_length=1, description="チャンクのテキスト内容")
    embedding: list[float] | None = Field(
        None, description="埋め込みベクトル（1536次元）"
    )
    metadata: ChunkMetadata = Field(..., description="チャンクのメタデータ")

    model_config = {"frozen": True}

    @property
    def has_embedding(self) -> bool:
        """埋め込みベクトルが設定されているかを判定する。"""
        return self.embedding is not None

    def with_embedding(self, embedding: list[float]) -> "DocumentChunk":
        """埋め込みベクトルを設定した新しいインスタンスを返す。

        Args:
            embedding: 埋め込みベクトル

        Returns:
            埋め込みベクトルが設定されたDocumentChunkインスタンス
        """
        return self.model_copy(update={"embedding": embedding})

    @classmethod
    def create(
        cls,
        document_id: DocumentId,
        content: str,
        chunk_index: int,
        start_position: int,
        end_position: int,
        total_chunks: int,
        overlap_with_previous: int = 0,
        overlap_with_next: int = 0,
    ) -> "DocumentChunk":
        """DocumentChunkの新規作成。

        Args:
            document_id: 所属する文書のID
            content: チャンクのテキスト内容
            chunk_index: チャンクのインデックス
            start_position: 開始位置
            end_position: 終了位置
            total_chunks: 総チャンク数
            overlap_with_previous: 前のチャンクとの重複文字数
            overlap_with_next: 次のチャンクとの重複文字数

        Returns:
            新しいDocumentChunkインスタンス
        """
        metadata = ChunkMetadata(
            chunk_index=chunk_index,
            start_position=start_position,
            end_position=end_position,
            total_chunks=total_chunks,
            overlap_with_previous=overlap_with_previous,
            overlap_with_next=overlap_with_next,
        )
        return cls(
            id=str(uuid.uuid4()),
            document_id=document_id,
            content=content,
            embedding=None,
            metadata=metadata,
        )
