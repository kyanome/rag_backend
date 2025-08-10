"""RAGパフォーマンステスト。

RAGシステムの応答時間、トークン使用量、並行処理性能をテストする。
"""

import asyncio
import time
from statistics import mean, stdev
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from src.domain.entities.rag_query import RAGQuery
from src.domain.value_objects import DocumentId, SearchResultItem
from src.domain.value_objects.rag_context import RAGContext
from src.infrastructure.externals.llms import MockLLMService
from src.infrastructure.externals.rag import RAGServiceImpl
from src.presentation.main import app


class TestRAGPerformance:
    """RAGパフォーマンステスト。"""

    @pytest.fixture
    def sample_search_results(self) -> list[SearchResultItem]:
        """サンプルの検索結果を生成する。"""
        results = []
        for i in range(10):
            results.append(
                SearchResultItem(
                    document_id=DocumentId(value=str(uuid4())),
                    document_title=f"文書{i}",
                    content_preview=f"これは文書{i}の内容です。" * 10,
                    score=0.9 - (i * 0.05),
                    match_type="both",
                    chunk_id=f"chunk{i}",
                    chunk_index=i,
                )
            )
        return results

    @pytest.fixture
    def large_context(
        self, sample_search_results: list[SearchResultItem]
    ) -> RAGContext:
        """大量の検索結果を含むコンテキストを生成する。"""
        unique_docs = len(set(item.document_id for item in sample_search_results))
        max_score = max((item.score for item in sample_search_results), default=0.0)
        
        return RAGContext(
            query_text="パフォーマンステスト用のクエリ",
            search_results=sample_search_results,
            context_text="",
            total_chunks=len(sample_search_results),
            unique_documents=unique_docs,
            max_relevance_score=max_score,
            metadata={"search_type": "hybrid"},
        )

    @pytest.mark.asyncio
    async def test_response_time_under_5_seconds(
        self, large_context: RAGContext
    ) -> None:
        """応答時間が5秒以内であることをテストする。"""
        llm_service = MockLLMService()
        rag_service = RAGServiceImpl(llm_service=llm_service)

        query = RAGQuery(
            query_text="パフォーマンステスト用のクエリです",
            max_results=10,
            temperature=0.7,
        )

        start_time = time.time()
        answer = await rag_service.process_query(query, large_context)
        end_time = time.time()

        response_time = end_time - start_time

        # 検証
        assert (
            response_time < 5.0
        ), f"Response time {response_time:.2f}s exceeds 5s limit"
        assert answer.answer_text
        assert answer.processing_time_ms >= 0  # 0以上であることを確認

    @pytest.mark.asyncio
    async def test_concurrent_requests_handling(self) -> None:
        """並行リクエストの処理をテストする。"""
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # 10個の並行リクエストを作成
            requests = []
            for i in range(10):
                request_data = {
                    "query": f"並行テストクエリ {i}",
                    "search_type": "hybrid",
                    "max_results": 5,
                    "temperature": 0.7,
                }
                requests.append(client.post("/api/v1/rag/query", json=request_data))

            # すべてのリクエストを並行実行
            start_time = time.time()
            responses = await asyncio.gather(*requests, return_exceptions=True)
            end_time = time.time()

            total_time = end_time - start_time

            # 検証
            successful_responses = [
                r
                for r in responses
                if not isinstance(r, Exception) and r.status_code == 200
            ]

            # 少なくとも80%のリクエストが成功することを確認
            success_rate = len(successful_responses) / len(responses)
            assert success_rate >= 0.8, f"Success rate {success_rate:.1%} is too low"

            # 並行処理が効率的であることを確認（総時間が個別時間の合計より短い）
            assert total_time < 20.0, f"Total time {total_time:.2f}s is too long"

    @pytest.mark.asyncio
    async def test_streaming_performance(self, large_context: RAGContext) -> None:
        """ストリーミング応答のパフォーマンスをテストする。"""
        llm_service = MockLLMService()
        rag_service = RAGServiceImpl(llm_service=llm_service)

        query = RAGQuery(
            query_text="ストリーミングパフォーマンステスト",
            max_results=5,
        )

        # 最初のチャンクまでの時間を測定
        start_time = time.time()
        first_chunk_time = None
        chunks_received = 0

        async for _chunk in rag_service.stream_answer(query, large_context):
            if first_chunk_time is None:
                first_chunk_time = time.time() - start_time
            chunks_received += 1

        end_time = time.time()
        total_time = end_time - start_time

        # 検証
        assert first_chunk_time is not None
        assert first_chunk_time < 1.0, f"First chunk took {first_chunk_time:.2f}s"
        assert chunks_received > 0
        assert total_time < 5.0, f"Total streaming time {total_time:.2f}s"

    @pytest.mark.asyncio
    async def test_token_usage_tracking(self, large_context: RAGContext) -> None:
        """トークン使用量の追跡をテストする。"""
        llm_service = MockLLMService()
        rag_service = RAGServiceImpl(llm_service=llm_service)

        queries = [
            "短いクエリ",
            "これは少し長めのクエリテキストです。詳細な情報を求めています。",
            "非常に長いクエリテキストで、多くの情報を含んでいます。" * 5,
        ]

        token_usages = []

        for query_text in queries:
            query = RAGQuery(query_text=query_text, max_results=5)
            answer = await rag_service.process_query(query, large_context)

            # トークン使用量を記録
            if answer.token_usage:
                token_usages.append(answer.token_usage)

        # 検証
        assert len(token_usages) == len(queries)

        # クエリが長いほどトークン使用量が増えることを確認
        for i in range(len(token_usages) - 1):
            assert (
                token_usages[i]["prompt_tokens"] <= token_usages[i + 1]["prompt_tokens"]
            )

    @pytest.mark.asyncio
    async def test_response_time_statistics(self, large_context: RAGContext) -> None:
        """複数回の応答時間の統計をテストする。"""
        llm_service = MockLLMService()
        rag_service = RAGServiceImpl(llm_service=llm_service)

        query = RAGQuery(
            query_text="統計テスト用クエリ",
            max_results=5,
        )

        response_times = []

        # 10回実行して統計を取る
        for _ in range(10):
            start_time = time.time()
            await rag_service.generate_answer(query, large_context)
            end_time = time.time()
            response_times.append(end_time - start_time)

        # 統計計算
        avg_time = mean(response_times)
        std_time = stdev(response_times) if len(response_times) > 1 else 0
        max_time = max(response_times)

        # 検証
        assert avg_time < 2.0, f"Average response time {avg_time:.2f}s is too high"
        assert max_time < 5.0, f"Max response time {max_time:.2f}s exceeds limit"
        assert std_time < 1.0, f"Response time variance {std_time:.2f}s is too high"

        # 95パーセンタイルが5秒以内
        sorted_times = sorted(response_times)
        percentile_95 = sorted_times[int(len(sorted_times) * 0.95)]
        assert percentile_95 < 5.0, f"95th percentile {percentile_95:.2f}s exceeds 5s"

    @pytest.mark.asyncio
    async def test_memory_efficient_processing(self) -> None:
        """メモリ効率的な処理をテストする。"""
        # 大量の検索結果を生成
        huge_results = []
        for i in range(100):
            huge_results.append(
                SearchResultItem(
                    document_id=DocumentId(value=str(uuid4())),
                    document_title=f"大規模文書{i}",
                    content_preview="x" * 1000,  # 1KB of text
                    score=0.5,
                    match_type="both",
                    chunk_id=f"chunk{i}",
                    chunk_index=i,
                )
            )

        unique_docs = len(set(item.document_id for item in huge_results))
        max_score = max((item.score for item in huge_results), default=0.0)
        
        huge_context = RAGContext(
            query_text="メモリ効率テスト",
            search_results=huge_results,
            context_text="",
            total_chunks=len(huge_results),
            unique_documents=unique_docs,
            max_relevance_score=max_score,
            metadata={"search_type": "hybrid"},
        )

        llm_service = MockLLMService()
        rag_service = RAGServiceImpl(llm_service=llm_service)

        query = RAGQuery(
            query_text="メモリ効率テスト",
            max_results=100,
        )

        # メモリ使用量が爆発しないことを確認（エラーが出ないこと）
        answer = await rag_service.process_query(query, huge_context)

        # 検証
        assert answer.answer_text
        assert len(answer.citations) <= 100

    @pytest.mark.asyncio
    async def test_citation_extraction_performance(
        self, large_context: RAGContext
    ) -> None:
        """引用抽出のパフォーマンスをテストする。"""
        llm_service = MockLLMService()
        rag_service = RAGServiceImpl(llm_service=llm_service)

        # 多くの引用を含む長い回答テキスト
        long_answer = ""
        for i in range(50):
            long_answer += f"これは[Document {i % 10 + 1}]からの情報です。"

        # 引用抽出の時間を測定
        start_time = time.time()
        citations = rag_service.extract_citations(long_answer, large_context)
        end_time = time.time()

        extraction_time = end_time - start_time

        # 検証
        assert extraction_time < 1.0, f"Citation extraction took {extraction_time:.2f}s"
        assert len(citations) > 0
        assert len(citations) <= 10  # 重複が除去されている
