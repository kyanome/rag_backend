"""RAGコンテキスト値オブジェクトのテスト。"""

import pytest

from src.domain.value_objects import DocumentId, SearchResultItem
from src.domain.value_objects.rag_context import RAGContext


class TestRAGContext:
    """RAGContext値オブジェクトのテスト。"""

    def test_create_empty_context(self):
        """空のコンテキストを作成できる。"""
        context = RAGContext(
            query_text="test query",
            search_results=[],
            context_text="",
            total_chunks=0,
            unique_documents=0,
            max_relevance_score=0.0,
        )

        assert context.query_text == "test query"
        assert context.search_results == []
        assert context.context_text == ""
        assert context.total_chunks == 0
        assert context.unique_documents == 0
        assert context.max_relevance_score == 0.0

    def test_create_context_with_results(self):
        """検索結果付きコンテキストを作成できる。"""
        results = [
            SearchResultItem(
                document_id=DocumentId(value="550e8400-e29b-41d4-a716-446655440001"),
                document_title="Doc 1",
                content_preview="Content 1",
                score=0.9,
                match_type="vector",
            ),
            SearchResultItem(
                document_id=DocumentId(value="550e8400-e29b-41d4-a716-446655440002"),
                document_title="Doc 2",
                content_preview="Content 2",
                score=0.8,
                match_type="keyword",
            ),
        ]

        context = RAGContext(
            query_text="test query",
            search_results=results,
            context_text="Combined context",
            total_chunks=2,
            unique_documents=2,
            max_relevance_score=0.9,
        )

        assert len(context.search_results) == 2
        assert context.total_chunks == 2
        assert context.unique_documents == 2
        assert context.max_relevance_score == 0.9

    def test_context_from_search_results(self):
        """検索結果からコンテキストを構築できる。"""
        results = [
            SearchResultItem(
                document_id=DocumentId(value="550e8400-e29b-41d4-a716-446655440001"),
                document_title="Document One",
                content_preview="This is the first document content.",
                score=0.95,
                match_type="both",
            ),
            SearchResultItem(
                document_id=DocumentId(value="550e8400-e29b-41d4-a716-446655440002"),
                document_title="Document Two",
                content_preview="This is the second document content.",
                score=0.85,
                match_type="vector",
            ),
        ]

        context = RAGContext.from_search_results(
            query_text="test query",
            search_results=results,
            max_context_length=200,
        )

        assert context.query_text == "test query"
        assert context.total_chunks == 2
        assert context.unique_documents == 2
        assert context.max_relevance_score == 0.95
        assert "[Document 1: Document One]" in context.context_text
        assert "[Document 2: Document Two]" in context.context_text

    def test_context_truncation(self):
        """長いコンテキストが切り詰められる。"""
        long_content = "x" * 500
        results = [
            SearchResultItem(
                document_id=DocumentId(value="550e8400-e29b-41d4-a716-446655440001"),
                document_title="Long Document",
                content_preview=long_content,
                score=0.9,
                match_type="both",
            ),
        ]

        context = RAGContext.from_search_results(
            query_text="test",
            search_results=results,
            max_context_length=100,
        )

        assert len(context.context_text) <= 100

    def test_is_sufficient(self):
        """コンテキストの十分性を判定できる。"""
        # 不十分なコンテキスト
        insufficient = RAGContext(
            query_text="test",
            search_results=[],
            context_text="",
            total_chunks=0,
            unique_documents=0,
            max_relevance_score=0.3,
        )
        assert insufficient.is_sufficient(min_chunks=1, min_score=0.5) is False

        # 十分なコンテキスト
        sufficient = RAGContext(
            query_text="test",
            search_results=[],
            context_text="context",
            total_chunks=3,
            unique_documents=2,
            max_relevance_score=0.8,
        )
        assert sufficient.is_sufficient(min_chunks=1, min_score=0.5) is True

    def test_get_document_titles(self):
        """文書タイトルのリストを取得できる。"""
        results = [
            SearchResultItem(
                document_id=DocumentId(value="550e8400-e29b-41d4-a716-446655440001"),
                document_title="Title A",
                content_preview="Content",
                score=0.9,
                match_type="vector",
            ),
            SearchResultItem(
                document_id=DocumentId(value="550e8400-e29b-41d4-a716-446655440002"),
                document_title="Title B",
                content_preview="Content",
                score=0.8,
                match_type="vector",
            ),
            SearchResultItem(
                document_id=DocumentId(value="550e8400-e29b-41d4-a716-446655440001"),
                document_title="Title A",  # 重複
                content_preview="Different content",
                score=0.7,
                match_type="keyword",
            ),
        ]

        context = RAGContext(
            query_text="test",
            search_results=results,
            context_text="",
            total_chunks=3,
            unique_documents=2,
            max_relevance_score=0.9,
        )

        titles = context.get_document_titles()
        assert titles == ["Title A", "Title B"]

    def test_get_top_results(self):
        """上位の検索結果を取得できる。"""
        results = [
            SearchResultItem(
                document_id=DocumentId(value=f"550e8400-e29b-41d4-a716-44665544000{i}"),
                document_title=f"Doc {i}",
                content_preview=f"Content {i}",
                score=0.9 - i * 0.1,
                match_type="both",
            )
            for i in range(5)
        ]

        context = RAGContext(
            query_text="test",
            search_results=results,
            context_text="",
            total_chunks=5,
            unique_documents=5,
            max_relevance_score=0.9,
        )

        top_3 = context.get_top_results(3)
        assert len(top_3) == 3
        assert top_3[0].document_title == "Doc 0"
        assert top_3[1].document_title == "Doc 1"
        assert top_3[2].document_title == "Doc 2"

    def test_to_prompt_context(self):
        """プロンプト用コンテキストを生成できる。"""
        results = [
            SearchResultItem(
                document_id=DocumentId(value="550e8400-e29b-41d4-a716-446655440001"),
                document_title="Title 1",
                content_preview="Content 1",
                score=0.9,
                match_type="both",
            ),
        ]

        context = RAGContext(
            query_text="test",
            search_results=results,
            context_text="[Document 1: Title 1]\nContent 1\n",
            total_chunks=1,
            unique_documents=1,
            max_relevance_score=0.9,
        )

        # スコアなし
        prompt_context = context.to_prompt_context(include_scores=False)
        assert "[1] Title 1" in prompt_context
        assert "Score:" not in prompt_context

        # スコアあり
        prompt_context_with_scores = context.to_prompt_context(include_scores=True)
        assert "Title 1" in prompt_context_with_scores
        assert "Score: 0.90" in prompt_context_with_scores

    def test_validate_search_results_limit(self):
        """検索結果の上限を検証できる。"""
        # 100件を超える検索結果
        import uuid

        results = [
            SearchResultItem(
                document_id=DocumentId(
                    value=str(uuid.UUID(int=i + 0x550E8400E29B41D4A716446655440000))
                ),
                document_title=f"Doc {i}",
                content_preview="Content",
                score=0.5,
                match_type="keyword",
            )
            for i in range(101)
        ]

        with pytest.raises(ValueError, match="Too many search results"):
            RAGContext(
                query_text="test",
                search_results=results,
                context_text="",
                total_chunks=101,
                unique_documents=101,
                max_relevance_score=0.5,
            )
