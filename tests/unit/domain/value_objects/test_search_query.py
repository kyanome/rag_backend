"""SearchQuery値オブジェクトのテスト。"""

import pytest

from src.domain.value_objects import SearchQuery, SearchType


class TestSearchQuery:
    """SearchQuery値オブジェクトのテストクラス。"""

    def test_create_keyword_search_query(self) -> None:
        """キーワード検索クエリの作成テスト。"""
        query = SearchQuery(
            query_text="テスト検索",
            search_type=SearchType.KEYWORD,
            limit=20,
            offset=0,
        )

        assert query.query_text == "テスト検索"
        assert query.search_type == SearchType.KEYWORD
        assert query.limit == 20
        assert query.offset == 0
        assert query.similarity_threshold == 0.7
        assert query.filters is None

    def test_create_vector_search_query(self) -> None:
        """ベクトル検索クエリの作成テスト。"""
        query = SearchQuery(
            query_text="類似文書検索",
            search_type=SearchType.VECTOR,
            similarity_threshold=0.85,
        )

        assert query.query_text == "類似文書検索"
        assert query.search_type == SearchType.VECTOR
        assert query.similarity_threshold == 0.85
        assert query.limit == 10  # デフォルト値

    def test_create_hybrid_search_query(self) -> None:
        """ハイブリッド検索クエリの作成テスト。"""
        filters = {"document_ids": ["doc1", "doc2"]}
        query = SearchQuery(
            query_text="ハイブリッド検索",
            search_type=SearchType.HYBRID,
            filters=filters,
        )

        assert query.query_text == "ハイブリッド検索"
        assert query.search_type == SearchType.HYBRID
        assert query.filters == filters

    def test_empty_query_text_raises_error(self) -> None:
        """空のクエリテキストでエラーが発生することを確認。"""
        with pytest.raises(ValueError, match="query_text cannot be empty"):
            SearchQuery(
                query_text="",
                search_type=SearchType.KEYWORD,
            )

    def test_whitespace_only_query_text_raises_error(self) -> None:
        """空白のみのクエリテキストでエラーが発生することを確認。"""
        with pytest.raises(ValueError, match="query_text cannot be empty"):
            SearchQuery(
                query_text="   ",
                search_type=SearchType.KEYWORD,
            )

    def test_query_text_too_long_raises_error(self) -> None:
        """長すぎるクエリテキストでエラーが発生することを確認。"""
        long_text = "a" * 1001
        with pytest.raises(
            ValueError, match="query_text cannot exceed 1000 characters"
        ):
            SearchQuery(
                query_text=long_text,
                search_type=SearchType.KEYWORD,
            )

    def test_invalid_limit_raises_error(self) -> None:
        """無効なlimit値でエラーが発生することを確認。"""
        with pytest.raises(ValueError, match="limit must be between 1 and 100"):
            SearchQuery(
                query_text="test",
                search_type=SearchType.KEYWORD,
                limit=0,
            )

        with pytest.raises(ValueError, match="limit must be between 1 and 100"):
            SearchQuery(
                query_text="test",
                search_type=SearchType.KEYWORD,
                limit=101,
            )

    def test_invalid_offset_raises_error(self) -> None:
        """無効なoffset値でエラーが発生することを確認。"""
        with pytest.raises(ValueError, match="offset must be non-negative"):
            SearchQuery(
                query_text="test",
                search_type=SearchType.KEYWORD,
                offset=-1,
            )

    def test_invalid_similarity_threshold_raises_error(self) -> None:
        """無効な類似度閾値でエラーが発生することを確認。"""
        with pytest.raises(ValueError, match="similarity_threshold must be between"):
            SearchQuery(
                query_text="test",
                search_type=SearchType.VECTOR,
                similarity_threshold=-0.1,
            )

        with pytest.raises(ValueError, match="similarity_threshold must be between"):
            SearchQuery(
                query_text="test",
                search_type=SearchType.VECTOR,
                similarity_threshold=1.1,
            )

    def test_is_keyword_search(self) -> None:
        """キーワード検索判定メソッドのテスト。"""
        keyword_query = SearchQuery(
            query_text="test",
            search_type=SearchType.KEYWORD,
        )
        vector_query = SearchQuery(
            query_text="test",
            search_type=SearchType.VECTOR,
        )

        assert keyword_query.is_keyword_search is True
        assert vector_query.is_keyword_search is False

    def test_is_vector_search(self) -> None:
        """ベクトル検索判定メソッドのテスト。"""
        vector_query = SearchQuery(
            query_text="test",
            search_type=SearchType.VECTOR,
        )
        keyword_query = SearchQuery(
            query_text="test",
            search_type=SearchType.KEYWORD,
        )

        assert vector_query.is_vector_search is True
        assert keyword_query.is_vector_search is False

    def test_is_hybrid_search(self) -> None:
        """ハイブリッド検索判定メソッドのテスト。"""
        hybrid_query = SearchQuery(
            query_text="test",
            search_type=SearchType.HYBRID,
        )
        keyword_query = SearchQuery(
            query_text="test",
            search_type=SearchType.KEYWORD,
        )

        assert hybrid_query.is_hybrid_search is True
        assert keyword_query.is_hybrid_search is False

    def test_needs_embedding(self) -> None:
        """埋め込み必要性判定メソッドのテスト。"""
        keyword_query = SearchQuery(
            query_text="test",
            search_type=SearchType.KEYWORD,
        )
        vector_query = SearchQuery(
            query_text="test",
            search_type=SearchType.VECTOR,
        )
        hybrid_query = SearchQuery(
            query_text="test",
            search_type=SearchType.HYBRID,
        )

        assert keyword_query.needs_embedding is False
        assert vector_query.needs_embedding is True
        assert hybrid_query.needs_embedding is True

    def test_needs_keyword_search(self) -> None:
        """キーワード検索必要性判定メソッドのテスト。"""
        keyword_query = SearchQuery(
            query_text="test",
            search_type=SearchType.KEYWORD,
        )
        vector_query = SearchQuery(
            query_text="test",
            search_type=SearchType.VECTOR,
        )
        hybrid_query = SearchQuery(
            query_text="test",
            search_type=SearchType.HYBRID,
        )

        assert keyword_query.needs_keyword_search is True
        assert vector_query.needs_keyword_search is False
        assert hybrid_query.needs_keyword_search is True

    def test_to_dict(self) -> None:
        """辞書変換メソッドのテスト。"""
        query = SearchQuery(
            query_text="test query",
            search_type=SearchType.HYBRID,
            limit=15,
            offset=5,
            similarity_threshold=0.8,
            filters={"key": "value"},
        )

        result = query.to_dict()

        assert result == {
            "query_text": "test query",
            "search_type": "hybrid",
            "limit": 15,
            "offset": 5,
            "similarity_threshold": 0.8,
            "filters": {"key": "value"},
        }

    def test_to_dict_with_no_filters(self) -> None:
        """フィルターなしの辞書変換テスト。"""
        query = SearchQuery(
            query_text="test",
            search_type=SearchType.KEYWORD,
        )

        result = query.to_dict()

        assert result["filters"] == {}

    def test_immutability(self) -> None:
        """不変性のテスト。"""
        query = SearchQuery(
            query_text="test",
            search_type=SearchType.KEYWORD,
        )

        # 値オブジェクトは不変なので、属性を変更しようとするとエラーになる
        with pytest.raises(AttributeError):
            query.query_text = "new text"  # type: ignore[misc]
