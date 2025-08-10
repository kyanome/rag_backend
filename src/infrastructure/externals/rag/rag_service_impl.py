"""RAGサービスの具体的な実装。

ドメイン層のRAGServiceインターフェースの実装を提供する。
"""

import re
from collections.abc import AsyncIterator

from ....domain.entities.rag_query import Citation, RAGAnswer, RAGQuery
from ....domain.externals import LLMService, RAGService
from ....domain.value_objects import (
    LLMMessage,
    LLMRequest,
    LLMRole,
    PromptTemplate,
    PromptVariable,
)
from ....domain.value_objects.rag_context import RAGContext


class RAGServiceImpl(RAGService):
    """RAGサービスの具体的な実装。

    プロンプト管理とLLM統合を提供する。
    """

    def __init__(
        self,
        llm_service: LLMService,
        system_prompt_template: PromptTemplate | None = None,
        user_prompt_template: PromptTemplate | None = None,
    ) -> None:
        """RAGサービスを初期化する。

        Args:
            llm_service: LLMサービス
            system_prompt_template: システムプロンプトテンプレート
            user_prompt_template: ユーザープロンプトテンプレート
        """
        self._llm_service = llm_service
        self._system_prompt_template = (
            system_prompt_template or self._get_default_system_prompt()
        )
        self._user_prompt_template = (
            user_prompt_template or self._get_default_user_prompt()
        )

    def _get_default_system_prompt(self) -> PromptTemplate:
        """デフォルトのシステムプロンプトを取得する。

        Returns:
            システムプロンプトテンプレート
        """
        return PromptTemplate(
            name="rag_system_prompt",
            template="""You are a knowledgeable AI assistant that provides accurate answers based on provided context.

Instructions:
1. Answer questions using ONLY the information from the provided context
2. If the context doesn't contain relevant information, clearly state that
3. Be concise and direct in your responses
4. Cite sources using [Document N] format when referencing specific information
5. Maintain a professional and helpful tone
6. Do not make up information not present in the context

Language: Respond in {language}""",
            variables=[
                PromptVariable(
                    name="language",
                    description="Response language",
                    required=False,
                    default="the same language as the question",
                ),
            ],
            description="Default RAG system prompt",
            version="1.0.0",
        )

    def _get_default_user_prompt(self) -> PromptTemplate:
        """デフォルトのユーザープロンプトを取得する。

        Returns:
            ユーザープロンプトテンプレート
        """
        return PromptTemplate(
            name="rag_user_prompt",
            template="""Context Information:
{context}

Question: {question}

Please provide a comprehensive answer based on the context above. If the context doesn't contain sufficient information to answer the question, please state that clearly.""",
            variables=[
                PromptVariable(
                    name="context",
                    description="Retrieved context",
                    required=True,
                    default=None,
                ),
                PromptVariable(
                    name="question",
                    description="User question",
                    required=True,
                    default=None,
                ),
            ],
            description="Default RAG user prompt",
            version="1.0.0",
        )

    async def process_query(
        self,
        query: RAGQuery,
        context: RAGContext,
    ) -> RAGAnswer:
        """RAGクエリを処理して応答を生成する。

        Args:
            query: RAGクエリ
            context: RAGコンテキスト

        Returns:
            RAG応答
        """
        # プロンプトを構築
        prompt = self.build_prompt(query, context)

        # LLMリクエストを作成
        messages = [
            LLMMessage(
                role=LLMRole.SYSTEM,
                content=self._system_prompt_template.format(language="Japanese"),
            ),
            LLMMessage(
                role=LLMRole.USER,
                content=prompt,
            ),
        ]

        llm_request = LLMRequest(
            messages=messages,
            model=self._llm_service.get_model_name(),
            temperature=query.temperature,
            max_tokens=1000,
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0,
            stop=None,
            stream=False,
        )

        # LLMで応答を生成
        llm_response = await self._llm_service.generate_response(llm_request)

        # RAG応答を作成
        answer = RAGAnswer(
            query_id=query.id,
            answer_text=llm_response.content,
            model_name=llm_response.model or self._llm_service.get_model_name(),
            token_usage={
                "prompt_tokens": llm_response.usage.prompt_tokens,
                "completion_tokens": llm_response.usage.completion_tokens,
                "total_tokens": llm_response.usage.total_tokens,
            },
        )

        # 引用を追加
        if query.include_citations:
            citations = self.extract_citations(llm_response.content, context)
            for citation in citations:
                answer.add_citation(citation)

        return answer

    async def stream_answer(
        self,
        query: RAGQuery,
        context: RAGContext,
    ) -> AsyncIterator[str]:
        """ストリーミング形式で応答を生成する。

        Args:
            query: RAGクエリ
            context: RAGコンテキスト

        Yields:
            応答テキストのチャンク
        """
        # プロンプトを構築
        prompt = self.build_prompt(query, context)

        # LLMリクエストを作成
        messages = [
            LLMMessage(
                role=LLMRole.SYSTEM,
                content=self._system_prompt_template.format(language="Japanese"),
            ),
            LLMMessage(
                role=LLMRole.USER,
                content=prompt,
            ),
        ]

        llm_request = LLMRequest(
            messages=messages,
            model=self._llm_service.get_model_name(),
            temperature=query.temperature,
            max_tokens=1000,
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0,
            stop=None,
            stream=True,
        )

        # ストリーミング応答を生成
        async for chunk in self._llm_service.stream_response(llm_request):
            if chunk.delta:
                yield chunk.delta

    def build_prompt(
        self,
        query: RAGQuery,
        context: RAGContext,
    ) -> str:
        """RAGプロンプトを構築する。

        Args:
            query: RAGクエリ
            context: RAGコンテキスト

        Returns:
            構築されたプロンプト
        """
        # コンテキストテキストを生成
        context_text = context.to_prompt_context(include_scores=False)

        # ユーザープロンプトをフォーマット
        prompt = self._user_prompt_template.format(
            context=context_text,
            question=query.query_text,
        )

        return prompt

    def extract_citations(
        self,
        answer_text: str,
        context: RAGContext,
    ) -> list[Citation]:
        """応答テキストから引用を抽出する。

        Args:
            answer_text: 応答テキスト
            context: RAGコンテキスト

        Returns:
            抽出された引用のリスト
        """
        citations: list[Citation] = []
        seen_citations = set()  # 重複チェック用

        # [Document N] または [N] 形式の引用を探す
        citation_patterns = [
            r"\[Document (\d+)\]",
            r"\[(\d+)\]",
        ]

        for pattern in citation_patterns:
            matches = list(re.finditer(pattern, answer_text))

            for match in matches:
                doc_index = int(match.group(1)) - 1  # 1-indexed to 0-indexed
                if 0 <= doc_index < len(context.search_results):
                    result = context.search_results[doc_index]

                    # 重複チェック用のキー
                    citation_key = (result.document_id, result.chunk_id)
                    if citation_key not in seen_citations:
                        citation = Citation.from_search_result(result)

                        # 引用位置情報を追加
                        citation.start_position = match.start()
                        citation.end_position = match.end()

                        # コンテキストを抽出（前後50文字）
                        context_range = 50
                        citation.context_before = answer_text[
                            max(0, match.start() - context_range) : match.start()
                        ].strip()
                        citation.context_after = answer_text[
                            match.end() : min(
                                len(answer_text), match.end() + context_range
                            )
                        ].strip()

                        citations.append(citation)
                        seen_citations.add(citation_key)

        # 引用が見つからない場合、コンテンツマッチングで引用を生成
        if not citations:
            citations = self._extract_citations_by_content(answer_text, context)

        return citations

    def _extract_citations_by_content(
        self,
        answer_text: str,
        context: RAGContext,
    ) -> list[Citation]:
        """コンテンツマッチングで引用を抽出する。

        Args:
            answer_text: 応答テキスト
            context: RAGコンテキスト

        Returns:
            抽出された引用のリスト
        """
        citations = []
        answer_lower = answer_text.lower()

        for result in context.search_results[:3]:  # 上位3件をチェック
            # タイトルまたは内容の一部が回答に含まれているかチェック
            title_match = result.document_title.lower() in answer_lower

            # 内容の重要な単語が含まれているかチェック
            content_words = result.content_preview.lower().split()[:20]
            content_match = (
                sum(
                    1
                    for word in content_words
                    if len(word) > 4 and word in answer_lower
                )
                >= 3
            )

            if title_match or content_match:
                citation = Citation.from_search_result(result)
                citations.append(citation)

        # 少なくとも1つの引用を含める
        if not citations and context.search_results:
            citations.append(Citation.from_search_result(context.search_results[0]))

        return citations

    def validate_answer(
        self,
        answer: RAGAnswer,
        query: RAGQuery,
    ) -> bool:
        """応答の妥当性を検証する。

        Args:
            answer: RAG応答
            query: 元のクエリ

        Returns:
            応答が妥当な場合True
        """
        # 基本的な検証
        if not answer.answer_text or len(answer.answer_text) < 10:
            return False

        # クエリに関連する内容が含まれているかチェック
        query_words = set(query.query_text.lower().split())
        answer_words = set(answer.answer_text.lower().split())

        # クエリの単語の少なくとも20%が回答に含まれている
        common_words = query_words & answer_words
        if len(common_words) < len(query_words) * 0.2:
            return False

        # 引用が必要な場合、引用があるかチェック
        if query.include_citations and not answer.has_citations:
            return False

        return True
