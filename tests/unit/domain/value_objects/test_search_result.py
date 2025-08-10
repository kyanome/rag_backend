"""SearchResult値オブジェクトのテスト。"""

import pytest

from src.domain.value_objects import (
    ConfidenceLevel,
    DocumentId,
    SearchResult,
    SearchResultItem,
    SearchType,
)


def create_doc_id(suffix: int = 1) -> str:
    """テスト用のUUID文字列を生成する。"""
    return f"12345678-1234-5678-1234-567890abcd{suffix:02d}"


class TestSearchResultItem:
    """SearchResultItem値オブジェクトのテストクラス。"""

    def test_create_keyword_search_result_item(self) -> None:
        """キーワード検索結果アイテムの作成テスト。"""
        doc_id = create_doc_id(1)
        item = SearchResultItem(
            document_id=DocumentId(value=doc_id),
            document_title="テスト文書",
            content_preview="これはテスト文書の内容です。",
            score=0.9,
            match_type="keyword",
            highlights=["テスト"],
        )

        assert item.document_id.value == doc_id
        assert item.document_title == "テスト文書"
        assert item.content_preview == "これはテスト文書の内容です。"
        assert item.score == 0.9
        assert item.match_type == "keyword"
        assert item.highlights == ["テスト"]
        assert item.chunk_id is None
        assert item.chunk_index is None

    def test_create_vector_search_result_item(self) -> None:
        """ベクトル検索結果アイテムの作成テスト。"""
        doc_id = create_doc_id(2)
        item = SearchResultItem(
            document_id=DocumentId(value=doc_id),
            document_title="類似文書",
            content_preview="類似した内容のプレビュー",
            score=0.75,
            match_type="vector",
            chunk_id="chunk001",
            chunk_index=5,
        )

        assert item.document_id.value == doc_id
        assert item.match_type == "vector"
        assert item.chunk_id == "chunk001"
        assert item.chunk_index == 5
        assert item.highlights is None

    def test_create_combined_search_result_item(self) -> None:
        """統合検索結果アイテムの作成テスト。"""
        doc_id = create_doc_id(3)
        item = SearchResultItem(
            document_id=DocumentId(value=doc_id),
            document_title="統合結果",
            content_preview="両方の検索にマッチ",
            score=0.95,
            match_type="both",
            chunk_id="chunk002",
            chunk_index=2,
            highlights=["マッチ"],
        )

        assert item.match_type == "both"
        assert item.chunk_id == "chunk002"
        assert item.highlights == ["マッチ"]

    def test_confidence_level_high(self) -> None:
        """高信頼度レベルのテスト。"""
        item = SearchResultItem(
            document_id=DocumentId(value=create_doc_id(1)),
            document_title="高信頼度文書",
            content_preview="内容",
            score=0.9,
            match_type="keyword",
        )

        assert item.confidence_level == ConfidenceLevel.HIGH
        assert item.is_high_confidence is True

    def test_confidence_level_medium(self) -> None:
        """中信頼度レベルのテスト。"""
        item = SearchResultItem(
            document_id=DocumentId(value=create_doc_id(2)),
            document_title="中信頼度文書",
            content_preview="内容",
            score=0.75,
            match_type="keyword",
        )

        assert item.confidence_level == ConfidenceLevel.MEDIUM
        assert item.is_high_confidence is False

    def test_confidence_level_low(self) -> None:
        """低信頼度レベルのテスト。"""
        item = SearchResultItem(
            document_id=DocumentId(value=create_doc_id(3)),
            document_title="低信頼度文書",
            content_preview="内容",
            score=0.5,
            match_type="keyword",
        )

        assert item.confidence_level == ConfidenceLevel.LOW
        assert item.is_high_confidence is False

    def test_empty_document_title_raises_error(self) -> None:
        """空の文書タイトルでエラーが発生することを確認。"""
        with pytest.raises(ValueError, match="document_title cannot be empty"):
            SearchResultItem(
                document_id=DocumentId(value=create_doc_id(1)),
                document_title="",
                content_preview="内容",
                score=0.8,
                match_type="keyword",
            )

    def test_empty_content_preview_raises_error(self) -> None:
        """空の内容プレビューでエラーが発生することを確認。"""
        with pytest.raises(ValueError, match="content_preview cannot be empty"):
            SearchResultItem(
                document_id=DocumentId(value=create_doc_id(1)),
                document_title="タイトル",
                content_preview="",
                score=0.8,
                match_type="keyword",
            )

    def test_invalid_score_raises_error(self) -> None:
        """無効なスコアでエラーが発生することを確認。"""
        with pytest.raises(ValueError, match="score must be between"):
            SearchResultItem(
                document_id=DocumentId(value=create_doc_id(1)),
                document_title="タイトル",
                content_preview="内容",
                score=1.5,
                match_type="keyword",
            )

    def test_invalid_match_type_raises_error(self) -> None:
        """無効なマッチタイプでエラーが発生することを確認。"""
        with pytest.raises(ValueError, match="match_type must be"):
            SearchResultItem(
                document_id=DocumentId(value=create_doc_id(1)),
                document_title="タイトル",
                content_preview="内容",
                score=0.8,
                match_type="invalid",
            )

    def test_negative_chunk_index_raises_error(self) -> None:
        """負のチャンクインデックスでエラーが発生することを確認。"""
        with pytest.raises(ValueError, match="chunk_index must be non-negative"):
            SearchResultItem(
                document_id=DocumentId(value=create_doc_id(1)),
                document_title="タイトル",
                content_preview="内容",
                score=0.8,
                match_type="vector",
                chunk_index=-1,
            )

    def test_is_from_keyword_search(self) -> None:
        """キーワード検索由来判定のテスト。"""
        keyword_item = SearchResultItem(
            document_id=DocumentId(value=create_doc_id(1)),
            document_title="タイトル",
            content_preview="内容",
            score=0.8,
            match_type="keyword",
        )
        vector_item = SearchResultItem(
            document_id=DocumentId(value=create_doc_id(2)),
            document_title="タイトル",
            content_preview="内容",
            score=0.8,
            match_type="vector",
        )
        both_item = SearchResultItem(
            document_id=DocumentId(value=create_doc_id(3)),
            document_title="タイトル",
            content_preview="内容",
            score=0.8,
            match_type="both",
        )

        assert keyword_item.is_from_keyword_search is True
        assert vector_item.is_from_keyword_search is False
        assert both_item.is_from_keyword_search is True

    def test_is_from_vector_search(self) -> None:
        """ベクトル検索由来判定のテスト。"""
        keyword_item = SearchResultItem(
            document_id=DocumentId(value=create_doc_id(1)),
            document_title="タイトル",
            content_preview="内容",
            score=0.8,
            match_type="keyword",
        )
        vector_item = SearchResultItem(
            document_id=DocumentId(value=create_doc_id(2)),
            document_title="タイトル",
            content_preview="内容",
            score=0.8,
            match_type="vector",
        )
        both_item = SearchResultItem(
            document_id=DocumentId(value=create_doc_id(3)),
            document_title="タイトル",
            content_preview="内容",
            score=0.8,
            match_type="both",
        )

        assert keyword_item.is_from_vector_search is False
        assert vector_item.is_from_vector_search is True
        assert both_item.is_from_vector_search is True

    def test_to_dict(self) -> None:
        """辞書変換メソッドのテスト。"""
        doc_id = create_doc_id(1)
        item = SearchResultItem(
            document_id=DocumentId(value=doc_id),
            document_title="テスト文書",
            content_preview="プレビュー",
            score=0.85,
            match_type="both",
            chunk_id="chunk001",
            chunk_index=3,
            highlights=["キーワード"],
        )

        result = item.to_dict()

        assert result == {
            "document_id": doc_id,
            "document_title": "テスト文書",
            "content_preview": "プレビュー",
            "score": 0.85,
            "match_type": "both",
            "confidence_level": "high",
            "chunk_id": "chunk001",
            "chunk_index": 3,
            "highlights": ["キーワード"],
        }


class TestSearchResult:
    """SearchResult値オブジェクトのテストクラス。"""

    def test_create_search_result(self) -> None:
        """検索結果の作成テスト。"""
        items = [
            SearchResultItem(
                document_id=DocumentId(value=create_doc_id(1)),
                document_title="文書1",
                content_preview="内容1",
                score=0.9,
                match_type="keyword",
            ),
            SearchResultItem(
                document_id=DocumentId(value=create_doc_id(2)),
                document_title="文書2",
                content_preview="内容2",
                score=0.8,
                match_type="vector",
            ),
        ]

        result = SearchResult(
            results=items,
            total_count=2,
            search_time_ms=150.5,
            query_type=SearchType.HYBRID,
            query_text="テスト検索",
        )

        assert len(result.results) == 2
        assert result.total_count == 2
        assert result.search_time_ms == 150.5
        assert result.query_type == SearchType.HYBRID
        assert result.query_text == "テスト検索"

    def test_empty_search_result(self) -> None:
        """空の検索結果の作成テスト。"""
        result = SearchResult(
            results=[],
            total_count=0,
            search_time_ms=10.0,
            query_type=SearchType.KEYWORD,
            query_text="見つからない検索",
        )

        assert result.has_results is False
        assert result.high_confidence_count == 0
        assert result.top_result is None

    def test_has_results(self) -> None:
        """結果存在判定のテスト。"""
        with_results = SearchResult(
            results=[
                SearchResultItem(
                    document_id=DocumentId(value=create_doc_id(1)),
                    document_title="文書",
                    content_preview="内容",
                    score=0.8,
                    match_type="keyword",
                )
            ],
            total_count=1,
            search_time_ms=10.0,
            query_type=SearchType.KEYWORD,
            query_text="test",
        )

        without_results = SearchResult(
            results=[],
            total_count=0,
            search_time_ms=10.0,
            query_type=SearchType.KEYWORD,
            query_text="test",
        )

        assert with_results.has_results is True
        assert without_results.has_results is False

    def test_high_confidence_count(self) -> None:
        """高信頼度カウントのテスト。"""
        items = [
            SearchResultItem(
                document_id=DocumentId(value=create_doc_id(i + 1)),
                document_title=f"文書{i}",
                content_preview=f"内容{i}",
                score=score,
                match_type="keyword",
            )
            for i, score in enumerate([0.9, 0.85, 0.75, 0.6])
        ]

        result = SearchResult(
            results=items,
            total_count=4,
            search_time_ms=10.0,
            query_type=SearchType.KEYWORD,
            query_text="test",
        )

        assert result.high_confidence_count == 2  # スコア >= 0.85 の数

    def test_top_result(self) -> None:
        """最上位結果取得のテスト。"""
        items = [
            SearchResultItem(
                document_id=DocumentId(value=create_doc_id(1)),
                document_title="最高スコア文書",
                content_preview="内容",
                score=0.95,
                match_type="keyword",
            ),
            SearchResultItem(
                document_id=DocumentId(value=create_doc_id(2)),
                document_title="二番目",
                content_preview="内容",
                score=0.8,
                match_type="keyword",
            ),
        ]

        result = SearchResult(
            results=items,
            total_count=2,
            search_time_ms=10.0,
            query_type=SearchType.KEYWORD,
            query_text="test",
        )

        assert result.top_result is not None
        assert result.top_result.document_title == "最高スコア文書"

    def test_filter_by_confidence(self) -> None:
        """信頼度によるフィルタリングのテスト。"""
        items = [
            SearchResultItem(
                document_id=DocumentId(value=create_doc_id(1)),
                document_title="高信頼",
                content_preview="内容",
                score=0.9,
                match_type="keyword",
            ),
            SearchResultItem(
                document_id=DocumentId(value=create_doc_id(2)),
                document_title="中信頼",
                content_preview="内容",
                score=0.75,
                match_type="keyword",
            ),
            SearchResultItem(
                document_id=DocumentId(value=create_doc_id(3)),
                document_title="低信頼",
                content_preview="内容",
                score=0.5,
                match_type="keyword",
            ),
        ]

        result = SearchResult(
            results=items,
            total_count=3,
            search_time_ms=10.0,
            query_type=SearchType.KEYWORD,
            query_text="test",
        )

        high_only = result.filter_by_confidence(ConfidenceLevel.HIGH)
        medium_and_above = result.filter_by_confidence(ConfidenceLevel.MEDIUM)
        all_results = result.filter_by_confidence(ConfidenceLevel.LOW)

        assert len(high_only) == 1
        assert len(medium_and_above) == 2
        assert len(all_results) == 3

    def test_results_not_sorted_raises_error(self) -> None:
        """ソートされていない結果でエラーが発生することを確認。"""
        items = [
            SearchResultItem(
                document_id=DocumentId(value=create_doc_id(1)),
                document_title="文書1",
                content_preview="内容",
                score=0.7,
                match_type="keyword",
            ),
            SearchResultItem(
                document_id=DocumentId(value=create_doc_id(2)),
                document_title="文書2",
                content_preview="内容",
                score=0.9,  # 前の要素より高いスコア
                match_type="keyword",
            ),
        ]

        with pytest.raises(ValueError, match="must be sorted by score"):
            SearchResult(
                results=items,
                total_count=2,
                search_time_ms=10.0,
                query_type=SearchType.KEYWORD,
                query_text="test",
            )

    def test_negative_total_count_raises_error(self) -> None:
        """負の総件数でエラーが発生することを確認。"""
        with pytest.raises(ValueError, match="total_count must be non-negative"):
            SearchResult(
                results=[],
                total_count=-1,
                search_time_ms=10.0,
                query_type=SearchType.KEYWORD,
                query_text="test",
            )

    def test_negative_search_time_raises_error(self) -> None:
        """負の検索時間でエラーが発生することを確認。"""
        with pytest.raises(ValueError, match="search_time_ms must be non-negative"):
            SearchResult(
                results=[],
                total_count=0,
                search_time_ms=-10.0,
                query_type=SearchType.KEYWORD,
                query_text="test",
            )

    def test_empty_query_text_raises_error(self) -> None:
        """空のクエリテキストでエラーが発生することを確認。"""
        with pytest.raises(ValueError, match="query_text cannot be empty"):
            SearchResult(
                results=[],
                total_count=0,
                search_time_ms=10.0,
                query_type=SearchType.KEYWORD,
                query_text="",
            )

    def test_to_dict(self) -> None:
        """辞書変換メソッドのテスト。"""
        items = [
            SearchResultItem(
                document_id=DocumentId(value=create_doc_id(1)),
                document_title="文書1",
                content_preview="内容1",
                score=0.9,
                match_type="keyword",
            ),
        ]

        result = SearchResult(
            results=items,
            total_count=1,
            search_time_ms=25.5,
            query_type=SearchType.HYBRID,
            query_text="検索クエリ",
        )

        dict_result = result.to_dict()

        assert dict_result["total_count"] == 1
        assert dict_result["search_time_ms"] == 25.5
        assert dict_result["query_type"] == "hybrid"
        assert dict_result["query_text"] == "検索クエリ"
        assert dict_result["high_confidence_count"] == 1
        assert len(dict_result["results"]) == 1
