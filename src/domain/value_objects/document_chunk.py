"""文書チャンク値オブジェクト。"""

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
