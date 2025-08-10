"""OpenAI API実統合テスト。

実際のOpenAI APIを使用してRAGシステムの動作を検証する。
環境変数OPENAI_API_KEYが必要。
"""

import os
from uuid import uuid4

import pytest
from dotenv import load_dotenv

from src.domain.entities.rag_query import RAGQuery
from src.domain.value_objects import DocumentId, SearchResultItem
from src.domain.value_objects.rag_context import RAGContext
from src.infrastructure.externals.llms import OpenAILLMService
from src.infrastructure.externals.rag import RAGServiceImpl

# .env.testファイルから環境変数を読み込む
load_dotenv(".env.test", override=True)


@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY")
    or os.getenv("OPENAI_API_KEY") == "your-openai-api-key-here",
    reason="OpenAI API key not configured in .env.test",
)
class TestOpenAIRealIntegration:
    """OpenAI API実統合テスト。"""

    @pytest.fixture
    def sample_search_results(self) -> list[SearchResultItem]:
        """テスト用の検索結果を生成する。"""
        return [
            SearchResultItem(
                document_id=DocumentId(value=str(uuid4())),
                document_title="人工知能の歴史",
                content_preview="人工知能（AI）の研究は1950年代に始まりました。アラン・チューリングが「機械は思考できるか」という問いを投げかけ、チューリングテストを提案しました。",
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
                document_title="深層学習の進化",
                content_preview="深層学習は、多層のニューラルネットワークを使用する機械学習の一分野です。画像認識、音声認識、自然言語処理などで革命的な成果を上げています。",
                score=0.75,
                match_type="both",
                chunk_id="chunk3",
                chunk_index=2,
            ),
        ]

    @pytest.fixture
    def rag_context(self, sample_search_results: list[SearchResultItem]) -> RAGContext:
        """テスト用のRAGコンテキストを生成する。"""
        unique_docs = len({item.document_id for item in sample_search_results})
        max_score = max((item.score for item in sample_search_results), default=0.0)

        return RAGContext(
            query_text="人工知能の歴史と発展について教えてください",
            search_results=sample_search_results,
            context_text="",
            total_chunks=len(sample_search_results),
            unique_documents=unique_docs,
            max_relevance_score=max_score,
            metadata={"search_type": "hybrid"},
        )

    @pytest.fixture
    def test_query(self) -> RAGQuery:
        """テスト用のRAGクエリを生成する。"""
        return RAGQuery(
            query_text="人工知能の歴史と発展について、主要な出来事を含めて説明してください。",
            search_type="hybrid",
            max_results=5,
            temperature=0.7,
            include_citations=True,
        )

    @pytest.mark.asyncio
    async def test_openai_basic_query(
        self,
        test_query: RAGQuery,
        rag_context: RAGContext,
    ) -> None:
        """OpenAI APIで基本的なクエリをテストする。"""
        # OpenAI LLMサービスを作成
        llm_service = OpenAILLMService(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
        )

        # RAGサービスを作成
        rag_service = RAGServiceImpl(llm_service=llm_service)

        # 回答を生成
        answer = await rag_service.process_query(
            query=test_query,
            context=rag_context,
        )

        # 検証
        assert answer.answer_text, "回答テキストが空です"
        assert len(answer.answer_text) > 100, "回答が短すぎます"
        assert answer.model_name.startswith(
            "gpt-3.5-turbo"
        )  # OpenAIは具体的なバージョン番号を返す

        # 日本語の回答になっているか確認
        japanese_chars = set(
            "あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん"
        )
        has_japanese = any(char in japanese_chars for char in answer.answer_text)
        assert has_japanese, "回答に日本語が含まれていません"

        # 引用の検証
        if answer.citations:
            for citation in answer.citations:
                assert citation.document_id
                assert citation.document_title
                assert citation.relevance_score >= 0.0

        print("\n✅ 回答生成成功:")
        print(f"- 文字数: {len(answer.answer_text)}")
        print(f"- 引用数: {len(answer.citations)}")
        print(f"- モデル: {answer.model_name}")
        print("\n回答内容（最初の200文字）:")
        print(answer.answer_text[:200] + "...")

    @pytest.mark.asyncio
    async def test_openai_streaming_response(
        self,
        test_query: RAGQuery,
        rag_context: RAGContext,
    ) -> None:
        """OpenAI APIでストリーミング応答をテストする。"""
        # OpenAI LLMサービスを作成
        llm_service = OpenAILLMService(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
        )

        # RAGサービスを作成
        rag_service = RAGServiceImpl(llm_service=llm_service)

        # ストリーミング応答を取得
        chunks: list[str] = []
        async for chunk in rag_service.stream_answer(
            query=test_query,
            context=rag_context,
        ):
            chunks.append(chunk)

        # 検証
        assert len(chunks) > 0, "チャンクが生成されませんでした"
        full_response = "".join(chunks)
        assert len(full_response) > 100, "ストリーミング応答が短すぎます"

        print("\n✅ ストリーミング成功:")
        print(f"- チャンク数: {len(chunks)}")
        print(f"- 合計文字数: {len(full_response)}")

    @pytest.mark.asyncio
    async def test_openai_with_different_temperatures(
        self,
        rag_context: RAGContext,
    ) -> None:
        """異なる温度設定でのOpenAI応答をテストする。"""
        llm_service = OpenAILLMService(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
        )
        rag_service = RAGServiceImpl(llm_service=llm_service)

        temperatures = [0.0, 0.5, 1.0]
        responses = []

        for temp in temperatures:
            query = RAGQuery(
                query_text="AIの主要な応用分野を3つ挙げてください。",
                temperature=temp,
                max_results=3,
            )

            answer = await rag_service.process_query(query, rag_context)
            responses.append(answer.answer_text)

            print(f"\n温度 {temp}: {answer.answer_text[:100]}...")

        # 温度0.0の応答は決定的であるべき
        assert responses[0], "温度0.0の応答が空です"

        # すべての応答が生成されていることを確認
        for i, resp in enumerate(responses):
            assert len(resp) > 0, f"温度{temperatures[i]}の応答が空です"

    @pytest.mark.asyncio
    async def test_openai_token_usage(
        self,
        test_query: RAGQuery,
        rag_context: RAGContext,
    ) -> None:
        """OpenAI APIのトークン使用量を確認する。"""
        llm_service = OpenAILLMService(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            model=os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
        )
        rag_service = RAGServiceImpl(llm_service=llm_service)

        answer = await rag_service.process_query(test_query, rag_context)

        # トークン使用量の検証
        assert answer.token_usage, "トークン使用量が記録されていません"
        assert answer.token_usage.get("prompt_tokens", 0) > 0
        assert answer.token_usage.get("completion_tokens", 0) > 0
        assert answer.token_usage.get("total_tokens", 0) > 0

        print("\n📊 トークン使用量:")
        print(f"- プロンプト: {answer.token_usage.get('prompt_tokens', 0)}")
        print(f"- 完了: {answer.token_usage.get('completion_tokens', 0)}")
        print(f"- 合計: {answer.token_usage.get('total_tokens', 0)}")

        # コスト概算（GPT-3.5-turboの場合）
        total_tokens = answer.token_usage.get("total_tokens", 0)
        estimated_cost = (total_tokens / 1000) * 0.002  # $0.002 per 1K tokens
        print(f"- 推定コスト: ${estimated_cost:.4f}")


if __name__ == "__main__":
    # 直接実行用
    pytest.main([__file__, "-xvs"])
