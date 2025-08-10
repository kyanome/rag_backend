"""RAGクエリエンティティのテスト。"""

from datetime import datetime
from uuid import UUID

import pytest

from src.domain.entities.rag_query import Citation, RAGAnswer, RAGQuery
from src.domain.value_objects import DocumentId, SearchResultItem, UserId


class TestRAGQuery:
    """RAGQueryエンティティのテスト。"""

    def test_create_rag_query(self):
        """RAGクエリを作成できる。"""
        query = RAGQuery(
            query_text="What is RAG?",
            search_type="hybrid",
            max_results=5,
            temperature=0.7,
        )

        assert query.query_text == "What is RAG?"
        assert query.search_type == "hybrid"
        assert query.max_results == 5
        assert query.temperature == 0.7
        assert query.include_citations is True
        assert isinstance(query.id, UUID)
        assert isinstance(query.created_at, datetime)

    def test_create_rag_query_with_user(self):
        """ユーザー付きRAGクエリを作成できる。"""
        user_id = UserId(value="550e8400-e29b-41d4-a716-446655440003")
        query = RAGQuery(
            query_text="What is RAG?",
            user_id=user_id,
        )

        assert query.user_id == user_id
        assert query.is_authenticated is True

    def test_create_rag_query_without_user(self):
        """ユーザーなしRAGクエリを作成できる。"""
        query = RAGQuery(query_text="What is RAG?")

        assert query.user_id is None
        assert query.is_authenticated is False

    def test_rag_query_empty_text_raises_error(self):
        """空のクエリテキストでエラーが発生する。"""
        with pytest.raises(ValueError, match="Query text cannot be empty"):
            RAGQuery(query_text="")

    def test_rag_query_invalid_max_results(self):
        """無効な最大結果数でエラーが発生する。"""
        with pytest.raises(ValueError, match="Max results must be at least 1"):
            RAGQuery(query_text="test", max_results=0)

    def test_rag_query_invalid_temperature(self):
        """無効な温度でエラーが発生する。"""
        with pytest.raises(ValueError, match="Temperature must be between"):
            RAGQuery(query_text="test", temperature=2.5)


class TestCitation:
    """Citationエンティティのテスト。"""

    def test_create_citation(self):
        """引用を作成できる。"""
        doc_id = DocumentId(value="550e8400-e29b-41d4-a716-446655440001")
        citation = Citation(
            document_id=doc_id,
            document_title="Test Document",
            chunk_id="chunk1",
            chunk_index=0,
            content_snippet="This is a test.",
            relevance_score=0.8,
        )

        assert citation.document_id == doc_id
        assert citation.document_title == "Test Document"
        assert citation.chunk_id == "chunk1"
        assert citation.chunk_index == 0
        assert citation.content_snippet == "This is a test."
        assert citation.relevance_score == 0.8

    def test_citation_invalid_score(self):
        """無効な関連性スコアでエラーが発生する。"""
        doc_id = DocumentId(value="550e8400-e29b-41d4-a716-446655440001")
        with pytest.raises(ValueError, match="Relevance score must be between"):
            Citation(
                document_id=doc_id,
                document_title="Test",
                relevance_score=1.5,
            )

    def test_citation_from_search_result(self):
        """検索結果から引用を作成できる。"""
        search_result = SearchResultItem(
            document_id=DocumentId(value="550e8400-e29b-41d4-a716-446655440001"),
            document_title="Test Document",
            content_preview="This is a test content.",
            score=0.9,
            match_type="both",
            chunk_id="chunk1",
            chunk_index=5,
        )

        citation = Citation.from_search_result(search_result)

        assert citation.document_id == search_result.document_id
        assert citation.document_title == "Test Document"
        assert citation.chunk_id == "chunk1"
        assert citation.chunk_index == 5
        assert citation.content_snippet == "This is a test content."
        assert citation.relevance_score == 0.9


class TestRAGAnswer:
    """RAGAnswerエンティティのテスト。"""

    def test_create_rag_answer(self):
        """RAG応答を作成できる。"""
        query_id = UUID("12345678-1234-5678-1234-567812345678")
        answer = RAGAnswer(
            query_id=query_id,
            answer_text="RAG is Retrieval-Augmented Generation.",
            confidence_score=0.85,
            search_results_count=5,
            processing_time_ms=1500.0,
            model_name="gpt-3.5-turbo",
        )

        assert answer.query_id == query_id
        assert answer.answer_text == "RAG is Retrieval-Augmented Generation."
        assert answer.confidence_score == 0.85
        assert answer.search_results_count == 5
        assert answer.processing_time_ms == 1500.0
        assert answer.model_name == "gpt-3.5-turbo"
        assert isinstance(answer.id, UUID)
        assert isinstance(answer.created_at, datetime)

    def test_rag_answer_empty_text_raises_error(self):
        """空の応答テキストでエラーが発生する。"""
        with pytest.raises(ValueError, match="Answer text cannot be empty"):
            RAGAnswer(answer_text="")

    def test_rag_answer_invalid_confidence(self):
        """無効な信頼度スコアでエラーが発生する。"""
        with pytest.raises(ValueError, match="Confidence score must be between"):
            RAGAnswer(answer_text="test", confidence_score=1.5)

    def test_rag_answer_invalid_processing_time(self):
        """負の処理時間でエラーが発生する。"""
        with pytest.raises(ValueError, match="Processing time cannot be negative"):
            RAGAnswer(answer_text="test", processing_time_ms=-100)

    def test_rag_answer_has_citations(self):
        """引用の有無を判定できる。"""
        answer = RAGAnswer(answer_text="test")
        assert answer.has_citations is False

        citation = Citation(
            document_id=DocumentId(value="550e8400-e29b-41d4-a716-446655440001"),
            document_title="Test",
            relevance_score=0.8,
        )
        answer.add_citation(citation)
        assert answer.has_citations is True

    def test_rag_answer_high_confidence(self):
        """高信頼度を判定できる。"""
        low_confidence = RAGAnswer(answer_text="test", confidence_score=0.5)
        assert low_confidence.high_confidence is False

        high_confidence = RAGAnswer(answer_text="test", confidence_score=0.85)
        assert high_confidence.high_confidence is True

    def test_rag_answer_calculate_average_relevance(self):
        """引用の平均関連性スコアを計算できる。"""
        answer = RAGAnswer(answer_text="test")

        # 引用がない場合は0.0
        assert answer.calculate_average_relevance() == 0.0

        # 引用を追加
        citations = [
            Citation(
                document_id=DocumentId(value=f"550e8400-e29b-41d4-a716-44665544000{i}"),
                document_title=f"Doc {i}",
                relevance_score=score,
            )
            for i, score in enumerate([0.8, 0.9, 0.7], 1)
        ]

        for citation in citations:
            answer.add_citation(citation)

        # 平均を計算
        expected = (0.8 + 0.9 + 0.7) / 3
        assert answer.calculate_average_relevance() == pytest.approx(expected)
