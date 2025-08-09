"""ベクトル検索結果の値オブジェクト。"""

from dataclasses import dataclass

from .document_id import DocumentId


@dataclass(frozen=True)
class VectorSearchResult:
    """ベクトル検索結果を表す値オブジェクト。

    不変オブジェクトとして実装され、検索結果の詳細を保持する。
    """

    chunk_id: str
    document_id: DocumentId
    content: str
    similarity_score: float
    chunk_index: int
    document_title: str | None = None

    def __post_init__(self) -> None:
        """バリデーションを実行する。"""
        if not self.chunk_id:
            raise ValueError("chunk_id cannot be empty")
        if not self.content:
            raise ValueError("content cannot be empty")
        if not 0.0 <= self.similarity_score <= 1.0:
            raise ValueError("similarity_score must be between 0.0 and 1.0")
        if self.chunk_index < 0:
            raise ValueError("chunk_index must be non-negative")

    @property
    def is_high_confidence(self) -> bool:
        """高信頼度の結果かどうかを判定する。

        Returns:
            類似度が0.85以上の場合True
        """
        return self.similarity_score >= 0.85

    @property
    def is_medium_confidence(self) -> bool:
        """中信頼度の結果かどうかを判定する。

        Returns:
            類似度が0.7以上0.85未満の場合True
        """
        return 0.7 <= self.similarity_score < 0.85

    @property
    def is_low_confidence(self) -> bool:
        """低信頼度の結果かどうかを判定する。

        Returns:
            類似度が0.7未満の場合True
        """
        return self.similarity_score < 0.7

    def to_dict(self) -> dict:
        """辞書形式に変換する。

        Returns:
            値オブジェクトの辞書表現
        """
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id.value,
            "content": self.content,
            "similarity_score": self.similarity_score,
            "chunk_index": self.chunk_index,
            "document_title": self.document_title,
            "confidence_level": self._get_confidence_level(),
        }

    def _get_confidence_level(self) -> str:
        """信頼度レベルを文字列で取得する。

        Returns:
            "high", "medium", "low"のいずれか
        """
        if self.is_high_confidence:
            return "high"
        elif self.is_medium_confidence:
            return "medium"
        else:
            return "low"
