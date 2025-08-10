"""実LLM統合テスト。

OpenAI APIとOllama のローカルLLMを使用した統合テストを実行する。
環境変数でLLMプロバイダーを制御する。
"""

import os

import pytest
from dotenv import load_dotenv

from uuid import uuid4

from src.domain.entities.rag_query import RAGQuery
from src.domain.value_objects import DocumentId, SearchResultItem
from src.domain.value_objects.rag_context import RAGContext
from src.infrastructure.externals.llms import (
    LLMServiceFactory,
    MockLLMService,
    OllamaLLMService,
    OpenAILLMService,
)
from src.infrastructure.externals.rag import RAGServiceImpl

# .envファイルから環境変数を読み込む
load_dotenv()


@pytest.fixture
def sample_search_results() -> list[SearchResultItem]:
    """サンプルの検索結果を生成する。"""
    return [
        SearchResultItem(
            document_id=DocumentId(value=str(uuid4())),
            document_title="RAGシステムの概要",
            content_preview="RAG（Retrieval-Augmented Generation）は、検索と生成を組み合わせた技術です。大規模言語モデルに外部知識を統合することで、より正確で信頼性の高い回答を生成できます。",
            score=0.95,
            match_type="both",
            chunk_id="chunk1",
            chunk_index=0,
        ),
        SearchResultItem(
            document_id=DocumentId(value=str(uuid4())),
            document_title="機械学習の基礎",
            content_preview="機械学習は、データからパターンを学習し、予測や分類を行う技術です。教師あり学習、教師なし学習、強化学習の3つの主要なアプローチがあります。",
            score=0.85,
            match_type="both",
            chunk_id="chunk2",
            chunk_index=1,
        ),
        SearchResultItem(
            document_id=DocumentId(value=str(uuid4())),
            document_title="自然言語処理入門",
            content_preview="自然言語処理（NLP）は、コンピュータが人間の言語を理解し、処理する技術です。トークン化、品詞タグ付け、構文解析などの基本的な処理から始まります。",
            score=0.75,
            match_type="both",
            chunk_id="chunk3",
            chunk_index=2,
        ),
    ]


@pytest.fixture
def sample_rag_context(sample_search_results: list[SearchResultItem]) -> RAGContext:
    """サンプルのRAGコンテキストを生成する。"""
    unique_docs = len(set(item.document_id for item in sample_search_results))
    max_score = max((item.score for item in sample_search_results), default=0.0)
    
    return RAGContext(
        query_text="RAGシステムとは何ですか？",
        search_results=sample_search_results,
        context_text="",
        total_chunks=len(sample_search_results),
        unique_documents=unique_docs,
        max_relevance_score=max_score,
        metadata={"search_type": "hybrid"},
    )


@pytest.fixture
def sample_query() -> RAGQuery:
    """サンプルのRAGクエリを生成する。"""
    return RAGQuery(
        query_text="RAGシステムとは何ですか？その特徴と利点を教えてください。",
        search_type="hybrid",
        max_results=5,
        temperature=0.7,
        include_citations=True,
    )


class TestLLMIntegration:
    """LLM統合テスト。"""

    @pytest.mark.skipif(
        os.getenv("LLM_PROVIDER") != "openai" or not os.getenv("OPENAI_API_KEY"),
        reason="OpenAI API key not configured",
    )
    @pytest.mark.asyncio
    async def test_openai_llm_service_real_query(
        self,
        sample_query: RAGQuery,
        sample_rag_context: RAGContext,
    ) -> None:
        """OpenAI LLMサービスで実際のクエリをテストする。"""
        # OpenAI LLMサービスを作成
        llm_service = OpenAILLMService(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            model_name=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
        )

        # RAGサービスを作成
        rag_service = RAGServiceImpl(llm_service=llm_service)

        # 回答を生成
        answer = await rag_service.process_query(
            query=sample_query,
            context=sample_rag_context,
        )

        # 検証
        assert answer.answer_text
        assert len(answer.answer_text) > 50  # 十分な長さの回答
        assert answer.citations  # 引用が含まれている
        assert answer.confidence_score > 0.5  # 適度な信頼度
        assert answer.model_name == os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

        # 引用の検証
        for citation in answer.citations:
            assert citation.document_id
            assert citation.document_title
            assert citation.relevance_score >= 0.0

    @pytest.mark.skipif(
        os.getenv("LLM_PROVIDER") != "ollama",
        reason="Ollama not configured as provider",
    )
    @pytest.mark.asyncio
    async def test_ollama_llm_service_real_query(
        self,
        sample_query: RAGQuery,
        sample_rag_context: RAGContext,
    ) -> None:
        """Ollama LLMサービスで実際のクエリをテストする。"""
        # Ollama LLMサービスを作成
        llm_service = OllamaLLMService(
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            model_name=os.getenv("OLLAMA_MODEL", "llama2"),
        )

        # Ollamaが実行中か確認
        try:
            # 簡単なテストクエリを送信
            test_response = await llm_service.generate(
                prompt="Hello",
                temperature=0.1,
                max_tokens=10,
            )
            if not test_response.content:
                pytest.skip("Ollama is not responding")
        except Exception:
            pytest.skip("Ollama is not running")

        # RAGサービスを作成
        rag_service = RAGServiceImpl(llm_service=llm_service)

        # 回答を生成
        answer = await rag_service.process_query(
            query=sample_query,
            context=sample_rag_context,
        )

        # 検証
        assert answer.answer_text
        assert len(answer.answer_text) > 30  # Ollamaは短めの回答でもOK
        assert answer.model_name == os.getenv("OLLAMA_MODEL", "llama2")

    @pytest.mark.asyncio
    async def test_streaming_response_with_mock_llm(
        self,
        sample_query: RAGQuery,
        sample_rag_context: RAGContext,
    ) -> None:
        """モックLLMでストリーミング応答をテストする。"""
        # モックLLMサービスを作成
        llm_service = MockLLMService()
        rag_service = RAGServiceImpl(llm_service=llm_service)

        # ストリーミング応答を取得
        chunks: list[str] = []
        async for chunk in rag_service.stream_answer(
            query=sample_query,
            context=sample_rag_context,
        ):
            chunks.append(chunk)

        # 検証
        assert len(chunks) > 0
        full_response = "".join(chunks)
        assert len(full_response) > 0  # モック応答が返されることを確認

    @pytest.mark.asyncio
    async def test_llm_service_factory(self) -> None:
        """LLMサービスファクトリーをテストする。"""
        # 環境変数を一時的に設定
        original_provider = os.getenv("LLM_PROVIDER")

        try:
            # Mockプロバイダー
            os.environ["LLM_PROVIDER"] = "mock"
            service = LLMServiceFactory.create(provider="mock")
            assert isinstance(service, MockLLMService)

            # OpenAIプロバイダー（APIキーがあれば）
            if os.getenv("OPENAI_API_KEY"):
                os.environ["LLM_PROVIDER"] = "openai"
                service = LLMServiceFactory.create(
                    provider="openai", 
                    api_key=os.getenv("OPENAI_API_KEY")
                )
                assert isinstance(service, OpenAILLMService)

            # Ollamaプロバイダー
            os.environ["LLM_PROVIDER"] = "ollama"
            service = LLMServiceFactory.create(provider="ollama")
            assert isinstance(service, OllamaLLMService)

        finally:
            # 元の環境変数を復元
            if original_provider:
                os.environ["LLM_PROVIDER"] = original_provider
            else:
                os.environ.pop("LLM_PROVIDER", None)

    @pytest.mark.asyncio
    async def test_error_handling_with_invalid_prompt(
        self,
        sample_rag_context: RAGContext,
    ) -> None:
        """無効なプロンプトでのエラーハンドリングをテストする。"""
        # 空のクエリ
        with pytest.raises(ValueError):
            RAGQuery(
                query_text="",  # 空のクエリ
                search_type="hybrid",
            )

        # 無効な温度パラメータ
        with pytest.raises(ValueError):
            RAGQuery(
                query_text="Test query",
                temperature=3.0,  # 範囲外
            )

    @pytest.mark.asyncio
    async def test_citation_extraction_with_multiple_formats(self) -> None:
        """複数の引用形式での抽出をテストする。"""
        llm_service = MockLLMService()
        rag_service = RAGServiceImpl(llm_service=llm_service)

        # 様々な引用形式を含む回答テキスト
        answer_texts = [
            "これは[Document 1]からの引用です。",
            "これは[1]からの引用です。",
            "複数の引用[Document 1]と[2]があります。",
        ]

        search_results = [
            SearchResultItem(
                document_id=DocumentId(value=str(uuid4())),
                document_title="文書1",
                content_preview="内容1",
                score=0.9,
                match_type="both",
            ),
            SearchResultItem(
                document_id=DocumentId(value=str(uuid4())),
                document_title="文書2",
                content_preview="内容2",
                score=0.8,
                match_type="both",
            ),
        ]
        
        sample_context = RAGContext(
            query_text="テストクエリ",
            search_results=search_results,
            context_text="",
            total_chunks=len(search_results),
            unique_documents=len(set(item.document_id for item in search_results)),
            max_relevance_score=max((item.score for item in search_results), default=0.0),
            metadata={"search_type": "hybrid"},
        )

        for answer_text in answer_texts:
            citations = rag_service.extract_citations(answer_text, sample_context)
            assert len(citations) > 0
            for citation in citations:
                assert citation.document_id
                assert citation.start_position is not None
                assert citation.end_position is not None
