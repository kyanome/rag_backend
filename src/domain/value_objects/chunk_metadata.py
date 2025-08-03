"""チャンクメタデータ値オブジェクト。"""

from pydantic import BaseModel, Field


class ChunkMetadata(BaseModel):
    """文書チャンクのメタデータを表す値オブジェクト。

    Attributes:
        chunk_index: チャンクのインデックス（0から開始）
        start_position: 元文書内での開始位置
        end_position: 元文書内での終了位置
        total_chunks: 文書全体のチャンク数
        overlap_with_previous: 前のチャンクとのオーバーラップ文字数
        overlap_with_next: 次のチャンクとのオーバーラップ文字数
    """

    chunk_index: int = Field(..., ge=0, description="チャンクのインデックス")
    start_position: int = Field(..., ge=0, description="元文書内での開始位置")
    end_position: int = Field(..., gt=0, description="元文書内での終了位置")
    total_chunks: int = Field(..., gt=0, description="文書全体のチャンク数")
    overlap_with_previous: int = Field(
        default=0, ge=0, description="前のチャンクとのオーバーラップ文字数"
    )
    overlap_with_next: int = Field(
        default=0, ge=0, description="次のチャンクとのオーバーラップ文字数"
    )

    model_config = {"frozen": True}

    @property
    def chunk_size(self) -> int:
        """チャンクのサイズを返す。"""
        return self.end_position - self.start_position

    @property
    def is_first_chunk(self) -> bool:
        """最初のチャンクかどうかを判定する。"""
        return self.chunk_index == 0

    @property
    def is_last_chunk(self) -> bool:
        """最後のチャンクかどうかを判定する。"""
        return self.chunk_index == self.total_chunks - 1
