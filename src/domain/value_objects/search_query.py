"""検索クエリ値オブジェクト。

DDDの原則に従い、検索クエリの表現と振る舞いをカプセル化する。
"""

from dataclasses import dataclass
from enum import Enum


class SearchType(Enum):
    """検索タイプを表す列挙型。

    システムがサポートする検索方式を定義する。
    """

    KEYWORD = "keyword"  # キーワード検索（全文検索）
    VECTOR = "vector"  # ベクトル類似検索
    HYBRID = "hybrid"  # ハイブリッド検索（キーワード+ベクトル）


@dataclass(frozen=True)
class SearchQuery:
    """検索クエリを表す値オブジェクト。

    不変オブジェクトとして実装され、検索条件を保持する。
    """

    query_text: str
    search_type: SearchType
    limit: int = 10
    offset: int = 0
    similarity_threshold: float = 0.7
    filters: dict | None = None

    def __post_init__(self) -> None:
        """バリデーションを実行する。"""
        if not self.query_text or not self.query_text.strip():
            raise ValueError("query_text cannot be empty")

        if len(self.query_text) > 1000:
            raise ValueError("query_text cannot exceed 1000 characters")

        if self.limit < 1 or self.limit > 100:
            raise ValueError("limit must be between 1 and 100")

        if self.offset < 0:
            raise ValueError("offset must be non-negative")

        if not 0.0 <= self.similarity_threshold <= 1.0:
            raise ValueError("similarity_threshold must be between 0.0 and 1.0")

    @property
    def is_keyword_search(self) -> bool:
        """キーワード検索かどうかを判定する。

        Returns:
            キーワード検索の場合True
        """
        return self.search_type == SearchType.KEYWORD

    @property
    def is_vector_search(self) -> bool:
        """ベクトル検索かどうかを判定する。

        Returns:
            ベクトル検索の場合True
        """
        return self.search_type == SearchType.VECTOR

    @property
    def is_hybrid_search(self) -> bool:
        """ハイブリッド検索かどうかを判定する。

        Returns:
            ハイブリッド検索の場合True
        """
        return self.search_type == SearchType.HYBRID

    @property
    def needs_embedding(self) -> bool:
        """埋め込みベクトル生成が必要かどうかを判定する。

        Returns:
            ベクトル検索またはハイブリッド検索の場合True
        """
        return self.search_type in [SearchType.VECTOR, SearchType.HYBRID]

    @property
    def needs_keyword_search(self) -> bool:
        """キーワード検索が必要かどうかを判定する。

        Returns:
            キーワード検索またはハイブリッド検索の場合True
        """
        return self.search_type in [SearchType.KEYWORD, SearchType.HYBRID]

    def to_dict(self) -> dict:
        """辞書形式に変換する。

        Returns:
            値オブジェクトの辞書表現
        """
        return {
            "query_text": self.query_text,
            "search_type": self.search_type.value,
            "limit": self.limit,
            "offset": self.offset,
            "similarity_threshold": self.similarity_threshold,
            "filters": self.filters or {},
        }
