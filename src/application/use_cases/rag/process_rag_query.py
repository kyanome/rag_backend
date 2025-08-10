"""RAGクエリ処理ユースケース。

検索拡張生成（RAG）のメインユースケースを実装する。
"""

import time
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, field_validator

from ....domain.entities.rag_query import Citation, RAGAnswer, RAGQuery
from ....domain.externals import RAGService
from ....domain.value_objects import UserId
from ....domain.value_objects.confidence_score import ConfidenceScore
from ..search_documents import SearchDocumentsInput, SearchDocumentsUseCase

if TYPE_CHECKING:
    from .build_rag_context import BuildRAGContextUseCase
    from .generate_rag_answer import GenerateRAGAnswerUseCase


class ProcessRAGQueryInput(BaseModel):
    """RAGクエリ処理の入力DTO。

    Attributes:
        query_text: クエリテキスト
        user_id: ユーザーID（オプション）
        search_type: 検索タイプ（keyword/vector/hybrid）
        max_results: 検索結果の最大数
        temperature: LLMの生成温度
        include_citations: 引用を含めるかどうか
        stream: ストリーミング応答を使用するか
        metadata: その他のメタデータ
    """

    query_text: str = Field(
        ..., min_length=1, max_length=1000, description="クエリテキスト"
    )
    user_id: str | None = Field(None, description="ユーザーID")
    search_type: str = Field(default="hybrid", description="検索タイプ")
    max_results: int = Field(default=5, ge=1, le=20, description="検索結果の最大数")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="LLMの生成温度")
    include_citations: bool = Field(default=True, description="引用を含めるかどうか")
    stream: bool = Field(default=False, description="ストリーミング応答")
    metadata: dict[str, Any] = Field(default_factory=dict, description="メタデータ")

    @field_validator("search_type")
    @classmethod
    def validate_search_type(cls, v: str) -> str:
        """検索タイプのバリデーション。"""
        valid_types = ["keyword", "vector", "hybrid"]
        if v not in valid_types:
            raise ValueError(f"search_type must be one of {valid_types}")
        return v

    def to_domain(self) -> RAGQuery:
        """ドメインモデルに変換する。

        Returns:
            RAGQueryエンティティ
        """
        return RAGQuery(
            query_text=self.query_text.strip(),
            user_id=UserId(value=self.user_id) if self.user_id else None,
            search_type=self.search_type,
            max_results=self.max_results,
            temperature=self.temperature,
            include_citations=self.include_citations,
            metadata=self.metadata,
        )


class CitationOutput(BaseModel):
    """引用の出力DTO。

    Attributes:
        document_id: 文書ID
        document_title: 文書タイトル
        chunk_id: チャンクID
        chunk_index: チャンクインデックス
        content_snippet: 内容の抜粋
        relevance_score: 関連性スコア
    """

    document_id: str = Field(..., description="文書ID")
    document_title: str = Field(..., description="文書タイトル")
    chunk_id: str | None = Field(None, description="チャンクID")
    chunk_index: int | None = Field(None, description="チャンクインデックス")
    content_snippet: str = Field(..., description="内容の抜粋")
    relevance_score: float = Field(..., ge=0.0, le=1.0, description="関連性スコア")

    @classmethod
    def from_domain(cls, citation: Citation) -> "CitationOutput":
        """ドメインモデルから変換する。

        Args:
            citation: 引用エンティティ

        Returns:
            引用の出力DTO
        """
        return cls(
            document_id=citation.document_id.value,
            document_title=citation.document_title,
            chunk_id=citation.chunk_id,
            chunk_index=citation.chunk_index,
            content_snippet=citation.content_snippet,
            relevance_score=citation.relevance_score,
        )


class ProcessRAGQueryOutput(BaseModel):
    """RAGクエリ処理の出力DTO。

    Attributes:
        answer_id: 応答ID
        query_id: クエリID
        answer_text: 応答テキスト
        citations: 引用情報のリスト
        confidence_score: 信頼度スコア
        confidence_level: 信頼度レベル
        search_results_count: 検索結果数
        processing_time_ms: 処理時間（ミリ秒）
        model_name: 使用したモデル名
        token_usage: トークン使用量
        metadata: その他のメタデータ
    """

    answer_id: str = Field(..., description="応答ID")
    query_id: str = Field(..., description="クエリID")
    answer_text: str = Field(..., description="応答テキスト")
    citations: list[CitationOutput] = Field(
        default_factory=list, description="引用情報"
    )
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="信頼度スコア")
    confidence_level: str = Field(..., description="信頼度レベル")
    search_results_count: int = Field(..., ge=0, description="検索結果数")
    processing_time_ms: float = Field(..., ge=0, description="処理時間（ミリ秒）")
    model_name: str = Field(..., description="使用したモデル名")
    token_usage: dict[str, int] = Field(
        default_factory=dict, description="トークン使用量"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="メタデータ")

    @classmethod
    def from_domain(
        cls, answer: RAGAnswer, confidence: ConfidenceScore
    ) -> "ProcessRAGQueryOutput":
        """ドメインモデルから変換する。

        Args:
            answer: RAG応答エンティティ
            confidence: 信頼度スコア

        Returns:
            出力DTO
        """
        return cls(
            answer_id=str(answer.id),
            query_id=str(answer.query_id) if answer.query_id else "",
            answer_text=answer.answer_text,
            citations=[CitationOutput.from_domain(c) for c in answer.citations],
            confidence_score=confidence.score,
            confidence_level=confidence.level.value,
            search_results_count=answer.search_results_count,
            processing_time_ms=answer.processing_time_ms,
            model_name=answer.model_name,
            token_usage=answer.token_usage,
            metadata=answer.metadata,
        )


class ProcessRAGQueryUseCase:
    """RAGクエリ処理ユースケース。

    検索、コンテキスト構築、回答生成を統合する。
    """

    def __init__(
        self,
        search_use_case: SearchDocumentsUseCase,
        build_context_use_case: "BuildRAGContextUseCase",
        generate_answer_use_case: "GenerateRAGAnswerUseCase",
        rag_service: RAGService,
    ) -> None:
        """ユースケースを初期化する。

        Args:
            search_use_case: 文書検索ユースケース
            build_context_use_case: コンテキスト構築ユースケース
            generate_answer_use_case: 回答生成ユースケース
            rag_service: RAGサービス
        """
        self._search_use_case = search_use_case
        self._build_context_use_case = build_context_use_case
        self._generate_answer_use_case = generate_answer_use_case
        self._rag_service = rag_service

    async def execute(self, input_dto: ProcessRAGQueryInput) -> ProcessRAGQueryOutput:
        """RAGクエリを処理する。

        Args:
            input_dto: 入力DTO

        Returns:
            出力DTO

        Raises:
            Exception: 処理中にエラーが発生した場合
        """
        start_time = time.time()
        query = input_dto.to_domain()

        try:
            # 1. 文書検索を実行
            search_input = SearchDocumentsInput(
                query=input_dto.query_text,
                search_type=input_dto.search_type,
                limit=input_dto.max_results,
            )
            search_result = await self._search_use_case.execute(search_input)

            # 2. コンテキストを構築
            context = await self._build_context_use_case.execute(
                query_text=input_dto.query_text,
                search_results=search_result.results,
            )

            # 3. 回答を生成
            answer = await self._generate_answer_use_case.execute(
                query=query,
                context=context,
            )

            # 4. 処理時間を記録
            processing_time_ms = (time.time() - start_time) * 1000
            answer.processing_time_ms = processing_time_ms
            answer.search_results_count = len(search_result.results)

            # 5. 信頼度スコアを計算
            confidence = ConfidenceScore.from_context_and_results(
                max_search_score=(
                    search_result.results[0].score if search_result.results else 0.0
                ),
                num_results=len(search_result.results),
                num_documents=context.unique_documents,
            )
            answer.confidence_score = confidence.score

            return ProcessRAGQueryOutput.from_domain(answer, confidence)

        except Exception as e:
            raise Exception(f"Failed to process RAG query: {e}") from e

    async def stream(self, input_dto: ProcessRAGQueryInput) -> AsyncIterator[str]:
        """ストリーミング形式でRAGクエリを処理する。

        Args:
            input_dto: 入力DTO

        Yields:
            応答テキストのチャンク

        Raises:
            Exception: 処理中にエラーが発生した場合
        """
        query = input_dto.to_domain()

        try:
            # 1. 文書検索を実行
            search_input = SearchDocumentsInput(
                query=input_dto.query_text,
                search_type=input_dto.search_type,
                limit=input_dto.max_results,
            )
            search_result = await self._search_use_case.execute(search_input)

            # 2. コンテキストを構築
            context = await self._build_context_use_case.execute(
                query_text=input_dto.query_text,
                search_results=search_result.results,
            )

            # 3. ストリーミング応答を生成
            async for chunk in self._rag_service.stream_answer(query, context):
                yield chunk

        except Exception as e:
            raise Exception(f"Failed to stream RAG response: {e}") from e
