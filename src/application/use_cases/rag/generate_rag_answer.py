"""RAG回答生成ユースケース。

LLMを使用してRAG回答を生成するユースケースを実装する。
"""

from ....domain.entities.rag_query import Citation, RAGAnswer, RAGQuery
from ....domain.externals import LLMService, RAGService
from ....domain.value_objects import LLMMessage, LLMRequest, LLMRole
from ....domain.value_objects.rag_context import RAGContext


class GenerateRAGAnswerUseCase:
    """RAG回答生成ユースケース。

    コンテキストとクエリからLLMを使用して回答を生成する。
    """

    def __init__(
        self,
        llm_service: LLMService,
        rag_service: RAGService,
        default_model: str = "gpt-3.5-turbo",
    ) -> None:
        """ユースケースを初期化する。

        Args:
            llm_service: LLMサービス
            rag_service: RAGサービス
            default_model: デフォルトのモデル名
        """
        self._llm_service = llm_service
        self._rag_service = rag_service
        self._default_model = default_model

    async def execute(
        self,
        query: RAGQuery,
        context: RAGContext,
    ) -> RAGAnswer:
        """RAG回答を生成する。

        Args:
            query: RAGクエリ
            context: RAGコンテキスト

        Returns:
            生成されたRAG回答

        Raises:
            Exception: 回答生成中にエラーが発生した場合
        """
        try:
            # プロンプトを構築
            prompt = self._rag_service.build_prompt(query, context)

            # LLMリクエストを作成
            messages = [
                LLMMessage(
                    role=LLMRole.SYSTEM,
                    content=self._get_system_prompt(),
                ),
                LLMMessage(
                    role=LLMRole.USER,
                    content=prompt,
                ),
            ]

            llm_request = LLMRequest(
                messages=messages,
                model=self._default_model,
                temperature=query.temperature,
                max_tokens=1000,
                top_p=1.0,
                frequency_penalty=0.0,
                presence_penalty=0.0,
                stop=None,
                stream=False,
            )

            # LLMで回答を生成
            llm_response = await self._llm_service.generate_response(llm_request)

            # RAG回答を作成
            answer = RAGAnswer(
                query_id=query.id,
                answer_text=llm_response.content,
                model_name=llm_response.model or self._default_model,
                token_usage={
                    "prompt_tokens": llm_response.usage.prompt_tokens,
                    "completion_tokens": llm_response.usage.completion_tokens,
                    "total_tokens": llm_response.usage.total_tokens,
                },
            )

            # 引用を追加（必要な場合）
            if query.include_citations:
                citations = self._extract_citations_from_context(
                    context, llm_response.content
                )
                for citation in citations:
                    answer.add_citation(citation)

            # 応答を検証
            if not self._rag_service.validate_answer(answer, query):
                answer.metadata["validation_warning"] = "Answer validation failed"

            return answer

        except Exception as e:
            raise Exception(f"Failed to generate RAG answer: {e}") from e

    def _get_system_prompt(self) -> str:
        """システムプロンプトを取得する。

        Returns:
            システムプロンプト
        """
        return """You are a helpful AI assistant that provides accurate and informative answers based on the given context.

Rules:
1. Answer questions based ONLY on the provided context
2. If the context doesn't contain enough information, say so clearly
3. Be concise but comprehensive
4. Cite sources when making specific claims
5. Maintain a professional and helpful tone
6. If asked about something not in the context, explain that you don't have that information

When citing sources, use the format: [Document N] where N is the document number from the context."""

    def _extract_citations_from_context(
        self,
        context: RAGContext,
        answer_text: str,
    ) -> list[Citation]:
        """コンテキストから引用を抽出する。

        Args:
            context: RAGコンテキスト
            answer_text: 回答テキスト

        Returns:
            抽出された引用のリスト
        """
        citations = []

        # 回答で参照されている文書を特定
        # シンプルな実装: 上位の検索結果を引用として使用
        for result in context.get_top_results(3):
            citation = Citation.from_search_result(result)

            # 回答テキストに文書タイトルや内容の一部が含まれているかチェック
            if result.document_title.lower() in answer_text.lower() or any(
                word in answer_text.lower()
                for word in result.content_preview.lower().split()[:10]
            ):
                citations.append(citation)

        # 引用がない場合、最も関連性の高い結果を1つ追加
        if not citations and context.search_results:
            citations.append(Citation.from_search_result(context.search_results[0]))

        return citations

    async def generate_with_fallback(
        self,
        query: RAGQuery,
        context: RAGContext,
        fallback_model: str | None = None,
    ) -> RAGAnswer:
        """フォールバック付きで回答を生成する。

        メインモデルが失敗した場合、フォールバックモデルを使用する。

        Args:
            query: RAGクエリ
            context: RAGコンテキスト
            fallback_model: フォールバックモデル名

        Returns:
            生成されたRAG回答
        """
        try:
            # メインモデルで生成を試みる
            return await self.execute(query, context)
        except Exception as e:
            if not fallback_model:
                raise

            # フォールバックモデルで再試行
            original_model = self._default_model
            try:
                self._default_model = fallback_model
                answer = await self.execute(query, context)
                answer.metadata["fallback_used"] = True
                answer.metadata["original_error"] = str(e)
                return answer
            finally:
                self._default_model = original_model
