"""検索結果値オブジェクト。

DDDの原則に従い、統合された検索結果の表現をカプセル化する。
"""

from dataclasses import dataclass
from enum import Enum

from .document_id import DocumentId
from .search_query import SearchType


class ConfidenceLevel(Enum):
    """検索結果の信頼度レベルを表す列挙型。"""

    HIGH = "high"  # 高信頼度（スコア >= 0.85）
    MEDIUM = "medium"  # 中信頼度（0.7 <= スコア < 0.85）
    LOW = "low"  # 低信頼度（スコア < 0.7）


@dataclass(frozen=True)
class SearchResultItem:
    """個別の検索結果アイテムを表す値オブジェクト。

    キーワード検索とベクトル検索の両方の結果を統一的に表現する。
    """

    document_id: DocumentId
    document_title: str
    content_preview: str
    score: float
    match_type: str  # "keyword", "vector", "both"
    chunk_id: str | None = None
    chunk_index: int | None = None
    highlights: list[str] | None = None

    def __post_init__(self) -> None:
        """バリデーションを実行する。"""
        if not self.document_title:
            raise ValueError("document_title cannot be empty")

        if not self.content_preview:
            raise ValueError("content_preview cannot be empty")

        if not 0.0 <= self.score <= 1.0:
            raise ValueError("score must be between 0.0 and 1.0")

        if self.match_type not in ["keyword", "vector", "both"]:
            raise ValueError("match_type must be 'keyword', 'vector', or 'both'")

        if self.chunk_index is not None and self.chunk_index < 0:
            raise ValueError("chunk_index must be non-negative")

    @property
    def confidence_level(self) -> ConfidenceLevel:
        """信頼度レベルを取得する。

        Returns:
            スコアに基づく信頼度レベル
        """
        if self.score >= 0.85:
            return ConfidenceLevel.HIGH
        elif self.score >= 0.7:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW

    @property
    def is_high_confidence(self) -> bool:
        """高信頼度の結果かどうかを判定する。

        Returns:
            信頼度レベルがHIGHの場合True
        """
        return self.confidence_level == ConfidenceLevel.HIGH

    @property
    def is_from_keyword_search(self) -> bool:
        """キーワード検索由来の結果かどうかを判定する。

        Returns:
            キーワード検索由来の場合True
        """
        return self.match_type in ["keyword", "both"]

    @property
    def is_from_vector_search(self) -> bool:
        """ベクトル検索由来の結果かどうかを判定する。

        Returns:
            ベクトル検索由来の場合True
        """
        return self.match_type in ["vector", "both"]

    def to_dict(self) -> dict:
        """辞書形式に変換する。

        Returns:
            値オブジェクトの辞書表現
        """
        return {
            "document_id": self.document_id.value,
            "document_title": self.document_title,
            "content_preview": self.content_preview,
            "score": self.score,
            "match_type": self.match_type,
            "confidence_level": self.confidence_level.value,
            "chunk_id": self.chunk_id,
            "chunk_index": self.chunk_index,
            "highlights": self.highlights or [],
        }


@dataclass(frozen=True)
class SearchResult:
    """統合検索結果を表す値オブジェクト。

    複数の検索タイプの結果を統合して保持する。
    """

    results: list[SearchResultItem]
    total_count: int
    search_time_ms: float
    query_type: SearchType
    query_text: str

    def __post_init__(self) -> None:
        """バリデーションを実行する。"""
        if self.total_count < 0:
            raise ValueError("total_count must be non-negative")

        if self.search_time_ms < 0:
            raise ValueError("search_time_ms must be non-negative")

        if not self.query_text:
            raise ValueError("query_text cannot be empty")

        # 結果はスコアの降順でソートされていることを保証
        if len(self.results) > 1:
            for i in range(len(self.results) - 1):
                if self.results[i].score < self.results[i + 1].score:
                    raise ValueError(
                        "results must be sorted by score in descending order"
                    )

    @property
    def has_results(self) -> bool:
        """検索結果が存在するかどうかを判定する。

        Returns:
            結果が1件以上ある場合True
        """
        return len(self.results) > 0

    @property
    def high_confidence_count(self) -> int:
        """高信頼度の結果数を取得する。

        Returns:
            高信頼度の結果数
        """
        return sum(1 for r in self.results if r.is_high_confidence)

    @property
    def top_result(self) -> SearchResultItem | None:
        """最も関連性の高い結果を取得する。

        Returns:
            最上位の検索結果、結果がない場合はNone
        """
        return self.results[0] if self.results else None

    def filter_by_confidence(
        self, min_level: ConfidenceLevel
    ) -> list[SearchResultItem]:
        """指定した信頼度レベル以上の結果をフィルタリングする。

        Args:
            min_level: 最小信頼度レベル

        Returns:
            フィルタリングされた結果リスト
        """
        level_order = {
            ConfidenceLevel.LOW: 0,
            ConfidenceLevel.MEDIUM: 1,
            ConfidenceLevel.HIGH: 2,
        }
        min_order = level_order[min_level]

        return [r for r in self.results if level_order[r.confidence_level] >= min_order]

    def to_dict(self) -> dict:
        """辞書形式に変換する。

        Returns:
            値オブジェクトの辞書表現
        """
        return {
            "results": [r.to_dict() for r in self.results],
            "total_count": self.total_count,
            "search_time_ms": self.search_time_ms,
            "query_type": self.query_type.value,
            "query_text": self.query_text,
            "high_confidence_count": self.high_confidence_count,
        }
