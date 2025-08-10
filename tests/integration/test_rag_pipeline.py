"""RAGパイプラインの統合テスト。"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from src.application.use_cases.rag import ProcessRAGQueryUseCase
from src.domain.entities.rag_query import RAGAnswer
from src.infrastructure.externals.llms import MockLLMService
from src.infrastructure.externals.rag import RAGServiceImpl
from src.presentation.dependencies import get_process_rag_query_use_case
from src.presentation.main import app


class TestRAGPipelineIntegration:
    """RAGパイプライン統合テスト。"""

    @pytest.fixture
    def mock_rag_use_case(self):
        """モックRAGユースケース。"""
        mock = AsyncMock(spec=ProcessRAGQueryUseCase)

        # 成功応答を設定
        mock.execute.return_value = MagicMock(
            answer_id="answer123",
            query_id="query123",
            answer_text="RAG stands for Retrieval-Augmented Generation.",
            citations=[],
            confidence_score=0.85,
            confidence_level="high",
            search_results_count=5,
            processing_time_ms=1500.0,
            model_name="mock-model",
            token_usage={
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
            },
            metadata={},
        )

        # ストリーミング応答を設定
        async def stream_generator():
            yield "This is "
            yield "a streaming "
            yield "RAG response."

        mock.stream.return_value = stream_generator()

        return mock

    @pytest.mark.asyncio
    async def test_rag_query_endpoint(self, mock_rag_use_case):
        """RAGクエリエンドポイントが正常に動作する。"""
        # 依存性を上書き
        app.dependency_overrides[get_process_rag_query_use_case] = (
            lambda: mock_rag_use_case
        )

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/rag/query",
                json={
                    "query": "What is RAG?",
                    "search_type": "hybrid",
                    "max_results": 5,
                    "temperature": 0.7,
                    "include_citations": True,
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "RAG stands for Retrieval-Augmented Generation."
        assert data["confidence_score"] == 0.85
        assert data["confidence_level"] == "high"
        assert data["model_name"] == "mock-model"

        # 依存性をクリア
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_rag_query_endpoint_validation_error(self):
        """RAGクエリエンドポイントでバリデーションエラーが発生する。"""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # 空のクエリ
            response = await client.post(
                "/api/v1/rag/query",
                json={
                    "query": "",
                    "search_type": "hybrid",
                },
            )

        assert response.status_code == 422  # Validation error

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # 無効な検索タイプ
            response = await client.post(
                "/api/v1/rag/query",
                json={
                    "query": "test",
                    "search_type": "invalid_type",
                },
            )

        # ビジネスロジックで検証されるため400が返される
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_rag_stream_endpoint(self, mock_rag_use_case):
        """RAGストリーミングエンドポイントが正常に動作する。"""
        # 依存性を上書き
        app.dependency_overrides[get_process_rag_query_use_case] = (
            lambda: mock_rag_use_case
        )

        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/rag/query/stream",
                json={
                    "query": "What is RAG?",
                    "stream": True,
                },
            )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/x-ndjson"

        # ストリーミング応答を確認
        content = response.text
        # NDJSON形式で送信されるため、JSONチャンクを含む
        # 応答テキストが含まれていることを確認
        assert "RAG response" in content
        assert '{"type": "done"}' in content

        # 依存性をクリア
        app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_rag_pipeline_with_mock_services(self):
        """モックサービスを使用したRAGパイプライン全体のテスト。"""
        # MockLLMServiceを使用
        llm_service = MockLLMService()
        rag_service = RAGServiceImpl(llm_service=llm_service)

        # プロンプトを構築
        from src.domain.entities.rag_query import RAGQuery
        from src.domain.value_objects.rag_context import RAGContext

        query = RAGQuery(query_text="What is Python?")
        context = RAGContext(
            query_text="What is Python?",
            search_results=[],
            context_text="Python is a programming language.",
            total_chunks=1,
            unique_documents=1,
            max_relevance_score=0.9,
        )

        # RAGサービスで処理
        answer = await rag_service.process_query(query, context)

        assert isinstance(answer, RAGAnswer)
        assert answer.answer_text  # MockLLMServiceが応答を返す
        assert answer.model_name == "mock-model"
        assert answer.query_id == query.id

    @pytest.mark.asyncio
    async def test_rag_service_prompt_building(self):
        """RAGサービスのプロンプト構築が正常に動作する。"""
        llm_service = MockLLMService()
        rag_service = RAGServiceImpl(llm_service=llm_service)

        from src.domain.entities.rag_query import RAGQuery
        from src.domain.value_objects import DocumentId, SearchResultItem
        from src.domain.value_objects.rag_context import RAGContext

        query = RAGQuery(query_text="What is machine learning?")

        # 検索結果を含むコンテキスト
        search_results = [
            SearchResultItem(
                document_id=DocumentId(value="550e8400-e29b-41d4-a716-446655440001"),
                document_title="ML Basics",
                content_preview="Machine learning is a subset of AI.",
                score=0.95,
                match_type="both",
            ),
        ]

        context = RAGContext.from_search_results(
            query_text="What is machine learning?",
            search_results=search_results,
        )

        # プロンプトを構築
        prompt = rag_service.build_prompt(query, context)

        assert "What is machine learning?" in prompt
        assert "ML Basics" in prompt
        assert "Machine learning is a subset of AI" in prompt

    @pytest.mark.asyncio
    async def test_rag_service_citation_extraction(self):
        """RAGサービスの引用抽出が正常に動作する。"""
        llm_service = MockLLMService()
        rag_service = RAGServiceImpl(llm_service=llm_service)

        from src.domain.value_objects import DocumentId, SearchResultItem
        from src.domain.value_objects.rag_context import RAGContext

        # 検索結果を含むコンテキスト
        search_results = [
            SearchResultItem(
                document_id=DocumentId(value="550e8400-e29b-41d4-a716-446655440001"),
                document_title="Document One",
                content_preview="First document content.",
                score=0.9,
                match_type="both",
            ),
            SearchResultItem(
                document_id=DocumentId(value="550e8400-e29b-41d4-a716-446655440002"),
                document_title="Document Two",
                content_preview="Second document content.",
                score=0.8,
                match_type="vector",
            ),
        ]

        context = RAGContext.from_search_results(
            query_text="test",
            search_results=search_results,
        )

        # [Document 1] 形式の引用を含む回答
        answer_with_citations = (
            "Based on [Document 1], the answer is X. "
            "Additionally, [Document 2] mentions Y."
        )

        citations = rag_service.extract_citations(answer_with_citations, context)

        assert len(citations) == 2
        assert citations[0].document_title == "Document One"
        assert citations[1].document_title == "Document Two"

        # 引用がない回答
        answer_without_citations = "This is an answer without explicit citations."
        citations_fallback = rag_service.extract_citations(
            answer_without_citations, context
        )

        # 少なくとも1つの引用が返される（フォールバック）
        assert len(citations_fallback) >= 1

    @pytest.mark.asyncio
    async def test_rag_service_answer_validation(self):
        """RAGサービスの回答検証が正常に動作する。"""
        llm_service = MockLLMService()
        rag_service = RAGServiceImpl(llm_service=llm_service)

        from src.domain.entities.rag_query import RAGAnswer, RAGQuery

        query = RAGQuery(
            query_text="What is artificial intelligence?",
            include_citations=True,
        )

        # 有効な回答（引用付き）
        from src.domain.entities.rag_query import Citation
        from src.domain.value_objects import DocumentId

        valid_answer = RAGAnswer(
            answer_text="Artificial intelligence is the simulation of human intelligence.",
            confidence_score=0.9,
        )
        # 引用を追加
        citation = Citation(
            document_id=DocumentId(value="550e8400-e29b-41d4-a716-446655440001"),
            document_title="AI Basics",
            relevance_score=0.9,
        )
        valid_answer.add_citation(citation)
        assert rag_service.validate_answer(valid_answer, query) is True

        # 短すぎる回答
        short_answer = RAGAnswer(
            answer_text="AI",
            confidence_score=0.9,
        )
        assert rag_service.validate_answer(short_answer, query) is False

        # 引用が必要だが含まれていない回答
        no_citation_answer = RAGAnswer(
            answer_text="This is a valid length answer about artificial intelligence.",
            confidence_score=0.9,
            citations=[],
        )
        assert rag_service.validate_answer(no_citation_answer, query) is False
