"""RAGクエリ処理ユースケースのテスト。"""

from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from src.application.use_cases.rag import (
    BuildRAGContextUseCase,
    GenerateRAGAnswerUseCase,
    ProcessRAGQueryInput,
    ProcessRAGQueryOutput,
    ProcessRAGQueryUseCase,
)
from src.application.use_cases.search_documents import (
    SearchDocumentsOutput,
    SearchDocumentsUseCase,
    SearchResultItemOutput,
)
from src.domain.entities.rag_query import Citation, RAGAnswer
from src.domain.externals import RAGService
from src.domain.value_objects import DocumentId
from src.domain.value_objects.rag_context import RAGContext


class TestProcessRAGQueryUseCase:
    """ProcessRAGQueryUseCaseのテスト。"""

    @pytest.fixture
    def mock_search_use_case(self):
        """モック検索ユースケース。"""
        mock = AsyncMock(spec=SearchDocumentsUseCase)
        mock.execute.return_value = SearchDocumentsOutput(
            results=[
                SearchResultItemOutput(
                    document_id="550e8400-e29b-41d4-a716-446655440001",
                    document_title="Test Document 1",
                    content_preview="This is test content 1.",
                    score=0.9,
                    match_type="both",
                    confidence_level="high",
                ),
                SearchResultItemOutput(
                    document_id="550e8400-e29b-41d4-a716-446655440002",
                    document_title="Test Document 2",
                    content_preview="This is test content 2.",
                    score=0.8,
                    match_type="vector",
                    confidence_level="medium",
                ),
            ],
            total_count=2,
            search_time_ms=100.0,
            query_type="hybrid",
            query_text="test query",
            high_confidence_count=1,
        )
        return mock

    @pytest.fixture
    def mock_build_context_use_case(self):
        """モックコンテキスト構築ユースケース。"""
        mock = AsyncMock(spec=BuildRAGContextUseCase)
        mock.execute.return_value = RAGContext(
            query_text="test query",
            search_results=[],
            context_text="Combined context from documents.",
            total_chunks=2,
            unique_documents=2,
            max_relevance_score=0.9,
        )
        return mock

    @pytest.fixture
    def mock_generate_answer_use_case(self):
        """モック回答生成ユースケース。"""
        mock = AsyncMock(spec=GenerateRAGAnswerUseCase)
        mock.execute.return_value = RAGAnswer(
            id=UUID("12345678-1234-5678-1234-567812345678"),
            answer_text="This is the RAG answer based on the context.",
            confidence_score=0.85,
            model_name="gpt-3.5-turbo",
            token_usage={
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
            },
            citations=[
                Citation(
                    document_id=DocumentId(
                        value="550e8400-e29b-41d4-a716-446655440001"
                    ),
                    document_title="Test Document 1",
                    content_snippet="This is test content 1.",
                    relevance_score=0.9,
                ),
            ],
        )
        return mock

    @pytest.fixture
    def mock_rag_service(self):
        """モックRAGサービス。"""
        mock = AsyncMock(spec=RAGService)
        mock.build_prompt.return_value = "Formatted prompt"
        mock.validate_answer.return_value = True
        return mock

    @pytest.fixture
    def use_case(
        self,
        mock_search_use_case,
        mock_build_context_use_case,
        mock_generate_answer_use_case,
        mock_rag_service,
    ):
        """テスト用ユースケース。"""
        return ProcessRAGQueryUseCase(
            search_use_case=mock_search_use_case,
            build_context_use_case=mock_build_context_use_case,
            generate_answer_use_case=mock_generate_answer_use_case,
            rag_service=mock_rag_service,
        )

    @pytest.mark.asyncio
    async def test_execute_success(self, use_case):
        """RAGクエリ処理が成功する。"""
        input_dto = ProcessRAGQueryInput(
            query_text="What is RAG?",
            search_type="hybrid",
            max_results=5,
            temperature=0.7,
            include_citations=True,
        )

        output = await use_case.execute(input_dto)

        assert isinstance(output, ProcessRAGQueryOutput)
        assert output.answer_text == "This is the RAG answer based on the context."
        assert output.confidence_score == pytest.approx(0.797, rel=0.01)
        assert output.confidence_level in ["high", "medium", "low", "very_low"]
        assert output.search_results_count == 2
        assert output.model_name == "gpt-3.5-turbo"
        assert len(output.citations) == 1
        assert output.citations[0].document_title == "Test Document 1"

    @pytest.mark.asyncio
    async def test_execute_with_user_id(self, use_case, mock_search_use_case):
        """ユーザーID付きでRAGクエリ処理が成功する。"""
        input_dto = ProcessRAGQueryInput(
            query_text="What is RAG?",
            user_id="550e8400-e29b-41d4-a716-446655440003",
            search_type="hybrid",
        )

        output = await use_case.execute(input_dto)

        assert isinstance(output, ProcessRAGQueryOutput)
        # SearchDocumentsInputが正しく作成されたことを確認
        mock_search_use_case.execute.assert_called_once()
        search_input = mock_search_use_case.execute.call_args[0][0]
        assert search_input.query == "What is RAG?"
        assert search_input.search_type == "hybrid"

    @pytest.mark.asyncio
    async def test_execute_without_citations(
        self, use_case, mock_generate_answer_use_case
    ):
        """引用なしでRAGクエリ処理が成功する。"""
        # 引用なしの回答を返すように設定
        mock_generate_answer_use_case.execute.return_value = RAGAnswer(
            answer_text="Answer without citations.",
            confidence_score=0.7,
            model_name="gpt-3.5-turbo",
            token_usage={
                "prompt_tokens": 50,
                "completion_tokens": 25,
                "total_tokens": 75,
            },
            citations=[],
        )

        input_dto = ProcessRAGQueryInput(
            query_text="What is RAG?",
            include_citations=False,
        )

        output = await use_case.execute(input_dto)

        assert output.answer_text == "Answer without citations."
        assert len(output.citations) == 0

    @pytest.mark.asyncio
    async def test_execute_error_handling(self, use_case, mock_search_use_case):
        """エラーハンドリングが機能する。"""
        mock_search_use_case.execute.side_effect = Exception("Search failed")

        input_dto = ProcessRAGQueryInput(query_text="What is RAG?")

        with pytest.raises(Exception, match="Failed to process RAG query"):
            await use_case.execute(input_dto)

    @pytest.mark.asyncio
    async def test_stream_success(
        self,
        use_case,
        mock_rag_service,
        mock_search_use_case,
        mock_build_context_use_case,
    ):
        """ストリーミング処理が成功する。"""

        # ストリーミング応答を設定
        async def stream_generator():
            yield "This is "
            yield "a streaming "
            yield "response."

        mock_rag_service.stream_answer.return_value = stream_generator()

        input_dto = ProcessRAGQueryInput(
            query_text="What is RAG?",
            stream=True,
        )

        chunks = []
        async for chunk in use_case.stream(input_dto):
            chunks.append(chunk)

        assert chunks == ["This is ", "a streaming ", "response."]
        mock_search_use_case.execute.assert_called_once()
        mock_build_context_use_case.execute.assert_called_once()
        mock_rag_service.stream_answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_stream_error_handling(self, use_case, mock_search_use_case):
        """ストリーミング処理のエラーハンドリングが機能する。"""
        mock_search_use_case.execute.side_effect = Exception("Search failed")

        input_dto = ProcessRAGQueryInput(
            query_text="What is RAG?",
            stream=True,
        )

        with pytest.raises(Exception, match="Failed to stream RAG response"):
            async for _ in use_case.stream(input_dto):
                pass

    def test_input_dto_validation(self):
        """入力DTOのバリデーションが機能する。"""
        # 無効な検索タイプ
        with pytest.raises(ValueError, match="search_type must be one of"):
            ProcessRAGQueryInput(
                query_text="test",
                search_type="invalid",
            )

        # 無効な最大結果数
        with pytest.raises(ValueError):
            ProcessRAGQueryInput(
                query_text="test",
                max_results=0,
            )

        # 無効な温度
        with pytest.raises(ValueError):
            ProcessRAGQueryInput(
                query_text="test",
                temperature=3.0,
            )

    def test_input_dto_to_domain(self):
        """入力DTOがドメインモデルに変換できる。"""
        input_dto = ProcessRAGQueryInput(
            query_text="  What is RAG?  ",
            user_id="550e8400-e29b-41d4-a716-446655440003",
            search_type="hybrid",
            max_results=10,
            temperature=0.5,
            include_citations=False,
            metadata={"source": "api"},
        )

        query = input_dto.to_domain()

        assert query.query_text == "What is RAG?"  # トリミングされる
        assert query.user_id.value == "550e8400-e29b-41d4-a716-446655440003"
        assert query.search_type == "hybrid"
        assert query.max_results == 10
        assert query.temperature == 0.5
        assert query.include_citations is False
        assert query.metadata == {"source": "api"}
